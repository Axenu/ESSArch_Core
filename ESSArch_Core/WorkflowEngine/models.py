"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from __future__ import unicode_literals

import importlib
import uuid

from celery import chain, group, states as celery_states

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.translation import ugettext as _

from picklefield.fields import PickledObjectField

from ESSArch_Core.util import available_tasks, sliceUntilAttr


class Process(models.Model):
    def _create_task(self, name):
        """
        Create and instantiate the task with the given name

        Args:
            name: The name of the task, including package and module
        """
        [module, task] = name.rsplit('.', 1)
        return getattr(importlib.import_module(module), task)()

    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = PickledObjectField(null=True, default=None, editable=False)

    def __unicode__(self):
        return self.name


class ProcessStep(Process):
    Type_CHOICES = (
        (0, "Receive new object"),
        (5, "The object is ready to remodel"),
        (9, "New object stable"),
        (10, "Object don't exist in AIS"),
        (11, "Object don't have any projectcode in AIS"),
        (12, "Object don't have any local policy"),
        (13, "Object already have an AIP!"),
        (14, "Object is not active!"),
        (19, "Object got a policy"),
        (20, "Object not updated from AIS"),
        (21, "Object not accepted in AIS"),
        (24, "Object accepted in AIS"),
        (25, "SIP validate"),
        (30, "Create AIP package"),
        (40, "Create package checksum"),
        (50, "AIP validate"),
        (60, "Try to remove IngestObject"),
        (1000, "Write AIP to longterm storage"),
        (1500, "Remote AIP"),
        (2009, "Remove temp AIP object OK"),
        (3000, "Archived"),
        (5000, "ControlArea"),
        (5100, "WorkArea"),
        (9999, "Deleted"),
    )

    name = models.CharField(max_length=256)
    type = models.IntegerField(null=True, choices=Type_CHOICES)
    user = models.CharField(max_length=45)
    parent_step = models.ForeignKey(
        'self',
        related_name='child_steps',
        on_delete=models.CASCADE,
        null=True
    )
    parent_step_pos = models.IntegerField(_('Parent step position'), default=0)
    time_created = models.DateTimeField(auto_now_add=True)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.CASCADE,
        related_name='steps',
        blank=True,
        null=True
    )
    hidden = models.BooleanField(default=False)
    parallel = models.BooleanField(default=False)

    def task_set(self):
        """
        Gets the unique tasks connected to the process, ignoring retries and
        undos.

        Returns:
            Unique tasks connected to the process, ignoring retries and undos
        """
        return self.tasks.filter(
            undo_type=False,
            retried=False
        ).order_by("processstep_pos")

    def run(self, direct=True):
        """
        Runs the process step by first running the child steps and then the
        tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed chain consisting of potential child steps followed by
            tasks if called directly. The chain "non-executed" if direct is
            false
        """

        func = group if self.parallel else chain

        child_steps = self.child_steps.all()
        tasks = self.tasks.all()

        step_canvas = func(s.run(direct=False) for s in child_steps)
        task_canvas = func(self._create_task(t.name).s(
            taskobj=t
        ) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        return workflow() if direct else workflow

    def run_eagerly(self, **kwargs):
        """
        Runs the step locally (as a "regular" function)
        """

        for c in self.child_steps.all():
            c.run_eagerly()

        for t in self.tasks.all():
            t.run_eagerly()

    def undo(self, only_failed=False, direct=True):
        """
        Undos the process step by first undoing all tasks and then the
        child steps.

        Args:
            only_failed: If true, only undo the failed tasks,
                undo all tasks otherwise

        Returns:
            AsyncResult/EagerResult if there is atleast one task or child
            steps, otherwise None
        """

        child_steps = self.child_steps.all()
        tasks = self.tasks.all()

        if only_failed:
            tasks = tasks.filter(status=celery_states.FAILURE)

        tasks = tasks.filter(
            undo_type=False,
            undone=False
        )

        attempt = uuid.uuid4()

        func = group if self.parallel else chain

        task_canvas = func(self._create_task(t.name).si(
            taskobj=t.create_undo_obj(attempt=attempt),
        ) for t in tasks.reverse())
        step_canvas = func(s.undo(direct=False) for s in child_steps.reverse())

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (task_canvas | step_canvas)

        return workflow() if direct else workflow

    def retry(self, direct=True):
        """
        Retries the process step by first retrying all child steps and then all
        failed tasks.

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            none
        """

        child_steps = self.child_steps.all()

        tasks = self.tasks.filter(
            undone=True,
            retried=False
        ).order_by('processstep_pos')

        func = group if self.parallel else chain
        attempt = uuid.uuid4()

        step_canvas = func(s.retry(direct=False) for s in child_steps)
        task_canvas = func(self._create_task(t.name).s(
            taskobj=t.create_retry_obj(attempt=attempt),
        ) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        return workflow() if direct else workflow

    def resume(self, direct=True):
        """
        Resumes the process step by running all pending child steps and tasks

        Args:
            direct: False if the step is called from a parent step,
                    true otherwise

        Returns:
            The executed workflow if direct is true, the workflow non-executed
            otherwise
        """

        func = group if self.parallel else chain

        child_steps = self.child_steps.filter(tasks__status=celery_states.PENDING)
        tasks = self.tasks.filter(undone=False, undo_type=False, status=celery_states.PENDING)

        step_canvas = func(s.run(direct=False) for s in child_steps)
        task_canvas = func(self._create_task(t.name).s(taskobj=t) for t in tasks)

        if not child_steps:
            workflow = task_canvas
        elif not tasks:
            workflow = step_canvas
        else:
            workflow = (step_canvas | task_canvas)

        return workflow() if direct else workflow

    @property
    def time_started(self):
        if self.tasks.exists():
            return self.tasks.first().time_started

    @property
    def time_done(self):
        if self.tasks.exists():
            return self.tasks.first().time_done

    def progress(self):
        """
        Gets the progress of the step based on its child steps and tasks

        Args:

        Returns:
            The progress calculated by progress/total where progress simply is
            the progress (0-100) of all the underlying tasks and the total is
            |child_steps| + |tasks|
        """

        child_steps = self.child_steps.all()
        progress = 0
        total = len(child_steps) + len(self.task_set())

        if total == 0:
            return 100

        progress += sum([c.progress() for c in child_steps])

        tasks = self.tasks.filter(
            undone=False,
            undo_type=False,
            retried=False
        )

        try:
            progress += tasks.aggregate(Sum("progress"))["progress__sum"]
        except:
            pass

        try:
            return progress / total
        except:
            return 0

    @property
    def status(self):
        """
        Gets the status of the step based on its child steps and tasks

        Args:

        Returns:
            Can be one of the following:
            SUCCESS, STARTED, FAILURE, PENDING

            Which is decided by five scenarios:

            * If there are no child steps nor tasks, then SUCCESS.
            * If there are child steps or tasks and they are all pending,
              then PENDING.
            * If a child step or task has started, then STARTED.
            * If a child step or task has failed, then FAILURE.
            * If all child steps and tasks have succeeded, then SUCCESS.
        """

        child_steps = self.child_steps.all()
        tasks = self.tasks.filter(undo_type=False, undone=False, retried=False)
        status = celery_states.SUCCESS

        if not child_steps and not tasks:
            return celery_states.SUCCESS

        for i in list(child_steps) + list(tasks):
            istatus = i.status
            if istatus == celery_states.STARTED:
                status = istatus
            if (istatus == celery_states.PENDING and
                    status != celery_states.STARTED):
                status = istatus
            if istatus == celery_states.FAILURE:
                return istatus

        return status

    @property
    def undone(self):
        """
        Gets the undone state of the step based on its tasks and child steps

        Args:

        Returns:
            True if one or more child steps and/or tasks have undone set to
            true, false otherwise
        """

        child_steps = self.child_steps.all()
        undone_child_steps = any(c.undone for c in child_steps)
        undone_tasks = self.tasks.filter(undone=True, retried=False).exists()

        return undone_child_steps or undone_tasks

    class Meta:
        db_table = u'ProcessStep'
        ordering = ('parent_step_pos', 'time_created')

        def __unicode__(self):
            return '%s - %s - archiveobject:%s' % (
                self.name,
                self.id,
                self.archiveobject.ObjectUUID
            )


class ProcessTask(Process):
    TASK_STATE_CHOICES = zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    )

    celery_id = models.UUIDField(
        _('celery id'), max_length=255, null=True, editable=False
    )
    name = models.CharField(max_length=255)
    step = models.BooleanField(default=False)
    _status = models.CharField(
        db_column='status', max_length=50, default=celery_states.PENDING,
        choices=TASK_STATE_CHOICES
    )
    responsible = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, related_name='tasks', null=True
    )
    params = PickledObjectField(null=True, default={})
    result_params = PickledObjectField(null=True)
    time_started = models.DateTimeField(_('started at'), null=True, blank=True)
    time_done = models.DateTimeField(_('done at'), null=True, blank=True)
    einfo = PickledObjectField(
        _('einfo'), blank=True, null=True, editable=False
    )
    hidden = models.BooleanField(editable=False, default=False, db_index=True)
    meta = PickledObjectField(null=True, default=None, editable=False)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, null=True)
    parent_pos = models.IntegerField(default=0)
    parallel = models.BooleanField(default=False)
    attempt = models.UUIDField(default=uuid.uuid4)
    progress = models.IntegerField(default=0)
    undo_type = models.BooleanField(editable=False, default=False)
    retried = models.ForeignKey('self', related_name='retried_task', on_delete=models.SET_NULL, null=True, default=None)
    undone = models.ForeignKey('self', related_name='undone_task', on_delete=models.SET_NULL, null=True, default=None)
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    log = PickledObjectField(null=True, default=None)

    @property
    def exception(self):
        if self.einfo:
            return "%s: %s" % (self.einfo.type.__name__, self.einfo.exception)

    @property
    def traceback(self):
        if self.einfo:
            return self.einfo.traceback

    def clean(self):
        """
        Validates the task
        """

        full_task_names = [k for k, v in available_tasks()]

        # Make sure that the task exists
        if not self.step and self.name not in full_task_names:
            raise ValidationError("Task '%s' does not exist." % self.name)

    @property
    def status(self):
        children = self.children.filter(undo_type=False, undone__isnull=True, retried__isnull=True)
        status = self._status

        if self.undone:
            if self.retried:
                self.retried.refresh_from_db()
                return self.retried.status
            else:
                return celery_states.PENDING

        if status == celery_states.FAILURE or not children:
            return status

        for c in children:
            cstatus = c.status
            if cstatus == celery_states.STARTED:
                status = cstatus
            if (cstatus == celery_states.PENDING and
                    status != celery_states.STARTED):
                status = cstatus
            if cstatus == celery_states.FAILURE:
                return cstatus

        return status

    @status.setter
    def status(self, value):
        self._status = value

    def run(self, direct=True):
        """
        Runs the task
        """

        func = group if self.parallel else chain
        children = self.children.all()
        children_canvas = func(s.run(direct=False) for s in children)

        if not self.step:
            t = self._create_task(self.name)
            subtask = t.s(taskobj=self).set(queue=t.queue)
            workflow = chain(subtask, children_canvas) if children else chain(subtask)
        else:
            workflow = children_canvas

        return workflow() if direct else workflow

    def run_eagerly(self):
        """
        Runs the task locally (as a "regular" function)
        """

        res = None

        if not self.step:
            t = self._create_task(self.name)
            res = t(taskobj=self, eager=True)

        for c in self.children.all():
            res = c.run_eagerly()

        return res

    def undo(self, only_failed=False, direct=True):
        """
        Undos the task
        """

        func = group if self.parallel else chain
        children = self.children.all()#.filter(time_started__isnull=False)
        if only_failed:
            children = children.filter(_status=celery_states.FAILURE)
        children_canvas = func(s.undo(direct=False) for s in children.reverse())


        if not self.step:
            t = self._create_task(self.name)
            subtask = t.s(taskobj=self.create_undo_obj()).set(queue=t.queue)
            workflow = chain(children_canvas, subtask) if children else chain(subtask)
        else:
            workflow = children_canvas

        return workflow() if direct else workflow

    def retry(self, direct=True):
        """
        Retries the task
        """

        func = group if self.parallel else chain
        children = self.children.filter(undone__isnull=False, retried__isnull=True)
        children_canvas = func(s.retry(direct=False) for s in children)

        if not self.step:
            t = self._create_task(self.name)
            subtask = t.s(taskobj=self.create_retry_obj()).set(queue=t.queue)
            workflow = chain(subtask, children_canvas) if children else chain(subtask)
        else:
            workflow = children_canvas

        return workflow() if direct else workflow

    def create_undo_obj(self, attempt=uuid.uuid4()):
        """
        Create a new task that will be used to undo this task,
        also marks this task as undone

        Args:
            attempt: Which attempt the new task belongs to
        """

        self.undone = ProcessTask.objects.create(
            parent=self.parent, name="%s undo" % self.name,
            params=self.params, parent_pos=self.parent_pos,
            undo_type=True, attempt=attempt, status="PREPARED",
            information_package=self.information_package,
            step=self.step,
        )

        self.save()
        return self.undone

    def create_retry_obj(self, attempt=uuid.uuid4()):
        """
        Create a new task that will be used to retry this task,
        also marks this task as retried

        Args:
            attempt: Which attempt the new task belongs to
        """

        self.retried = ProcessTask.objects.create(
            parent=self.parent, name=self.name, params=self.params,
            parent_pos=self.parent_pos, attempt=attempt,
            status="PREPARED", information_package=self.information_package,
            step=self.step,
        )

        self.save()
        return self.retried

    class Meta:
        db_table = 'ProcessTask'
        ordering = ('parent_pos', 'time_started')

        def __unicode__(self):
            return '%s - %s' % (self.name, self.id)
