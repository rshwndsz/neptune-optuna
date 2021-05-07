#
# Copyright (c) 2021, Neptune Labs Sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from typing import Union, Iterable

import optuna

try:
    # neptune-client=0.9.0 package structure
    import neptune.new as neptune
    from neptune.new.types import File
    from neptune.new.internal.utils import verify_type
except ImportError:
    # neptune-client=1.0.0 package structure
    import neptune
    from neptune.types import File
    from neptune.internal.utils import verify_type


class NeptuneCallback:
    def __init__(self,
                 run: neptune.Run,
                 base_namespace: str = '',
                 plots_update_freq: Union[int, str] = 1,
                 study_update_freq: Union[int, str] = 1,
                 vis_backend: str = 'plotly',
                 log_plot_contour: bool = True,
                 log_plot_edf: bool = True,
                 log_plot_parallel_coordinate: bool = True,
                 log_plot_param_importances: bool = True,
                 log_plot_pareto_front: bool = True,
                 log_plot_slice: bool = True,
                 log_plot_intermediate_values: bool = True,
                 log_plot_optimization_history: bool = True):

        verify_type('run', run, neptune.Run)
        verify_type('base_namespace', base_namespace, str)
        
        verify_type('log_plots_freq', plots_update_freq, (int, str, type(None)))
        verify_type('log_study_freq', study_update_freq, (int, str, type(None)))
        verify_type('vis_backend', vis_backend, (str, type(None)))
        verify_type('log_plot_contour', log_plot_contour, (bool, type(None)))
        verify_type('log_plot_edf', log_plot_edf, (bool, type(None)))
        verify_type('log_plot_parallel_coordinate', log_plot_parallel_coordinate, (bool, type(None)))
        verify_type('log_plot_param_importances', log_plot_param_importances, (bool, type(None)))
        verify_type('log_plot_pareto_front', log_plot_pareto_front, (bool, type(None)))
        verify_type('log_plot_slice', log_plot_slice, (bool, type(None)))
        verify_type('log_plot_intermediate_values', log_plot_intermediate_values, (bool, type(None)))
        verify_type('log_plot_optimization_history', log_plot_optimization_history, (bool, type(None)))

        self.run = run[base_namespace]
        self._vis_backend = vis_backend
        self._plots_update_freq = plots_update_freq
        self._study_update_freq = study_update_freq
        self._log_plot_contour = log_plot_contour
        self._log_plot_edf = log_plot_edf
        self._log_plot_parallel_coordinate = log_plot_parallel_coordinate
        self._log_plot_param_importances = log_plot_param_importances
        self._log_plot_pareto_front = log_plot_pareto_front
        self._log_plot_slice = log_plot_slice
        self._log_plot_intermediate_values = log_plot_intermediate_values
        self._log_plot_optimization_history = log_plot_optimization_history

    def __call__(self, study: optuna.Study, trial: optuna.trial.FrozenTrial):
        self._log_trial(trial)
        self._log_trial_distributions(trial)
        self._log_best_trials(study)
        self._log_study_details(study, trial)
        self._log_plots(study, trial)
        self._log_study(study, trial)

    def _log_trial(self, trial):
        self.run['trials'] = stringify_keys(log_all_trials([trial]))

    def _log_trial_distributions(self, trial):
        self.run['study/distributions'].log(trial.distributions)

    def _log_best_trials(self, study):
        self.run['best'] = stringify_keys(log_best_trials(study))

    def _log_study_details(self, study, trial):
        if trial._trial_id == 0:
            log_study_details(self.run, study)

    def _log_plots(self, study, trial):
        if self._should_log_plots(study, trial):
            log_plots(self.run, study,
                      backend=self._vis_backend,
                      log_plot_contour=self._log_plot_contour,
                      log_plot_edf=self._log_plot_edf,
                      log_plot_parallel_coordinate=self._log_plot_parallel_coordinate,
                      log_plot_param_importances=self._log_plot_param_importances,
                      log_plot_pareto_front=self._log_plot_pareto_front,
                      log_plot_slice=self._log_plot_slice,
                      log_plot_optimization_history=self._log_plot_optimization_history,
                      log_plot_intermediate_values=self._log_plot_intermediate_values,
                      )

    def _log_study(self, study, trial):
        if self._should_log_study(study, trial):
            log_study(self.run, study)

    def _should_log_plots(self, study: optuna.Study, trial: optuna.trial.FrozenTrial):
        if self._plots_update_freq == 'never':
            return False
        if self._plots_update_freq == 'last':
            if study._stop_flag: # TODO there seems to be no good condition for determining the last trial
                return True
        else:
            if trial._trial_id % self._plots_update_freq == 0:
                return True
        return False

    def _should_log_study(self, study: optuna.Study, trial: optuna.trial.FrozenTrial):
        if self._study_update_freq == 'never':
            return False
        if self._study_update_freq == 'last':
            if study._stop_flag: # TODO there seems to be no good condition for determining the last trial
                return True
        else:
            if trial._trial_id % self._study_update_freq == 0:
                return True
        return False


def stringify_keys(o):
    return {str(k): stringify_keys(v) for k, v in o.items()} if isinstance(o, dict) else o


def log_study_details(run, study: optuna.Study):
    run['study/study_name'] = study.study_name
    run['study/direction'] = study.direction
    run['study/directions'] = study.directions
    run['study/system_attrs'] = study.system_attrs
    run['study/user_attrs'] = study.user_attrs
    try:
        run['study/_study_id'] = study._study_id
        run['study/_storage'] = study._storage
    except AttributeError:
        pass


def log_study(run, study: optuna.Study):
    try:
        if type(study._storage) is optuna.storages._in_memory.InMemoryStorage:
            """pickle and log the study object to the 'study/study.pkl' path"""
            run['study/study_name'] = study.study_name
            run['study/storage_type'] = 'InMemoryStorage'
            run['study/study'] = File.as_pickle(study)
            pass
        else:
            run['study/study_name'] = study.study_name
            if isinstance(study._storage, optuna.storages.RedisStorage):
                run['study/storage_type'] = "RedisStorage"
                run['study/storage_url'] = study._storage._url
            elif isinstance(study._storage, optuna.storages._CachedStorage):
                run['study/storage_type'] = "RDBStorage"  # apparently CachedStorage typically wraps RDBStorage
                run['study/storage_url'] = study._storage._backend.url
            elif isinstance(study._storage, optuna.storages.RDBStorage):
                run['study/storage_type'] = "RDBStorage"
                run['study/storage_url'] = study._storage.url
            else:
                run['study/storage_type'] = "unknown storage type"
                run['study/storage_url'] = "unknown storage url"
    except AttributeError:
        pass


def export_pickle(obj):
    from io import BytesIO
    import pickle

    buffer = BytesIO()
    pickle.dump(obj, buffer)
    buffer.seek(0)

    return buffer


def load_study_from_run(run: neptune.Run):
    if run['study/storage_type'].fetch() == 'InMemoryStorage':
        return get_pickle(path='study/study', run=run)
    else:
        return optuna.load_study(study_name=run['study/study_name'].fetch(), storage=run['study/storage_url'].fetch())


def get_pickle(run: neptune.Run, path: str):
    import os
    import tempfile
    import pickle

    with tempfile.TemporaryDirectory() as d:
        run[path].download(destination=d)
        filepath = os.listdir(d)[0]
        full_path = os.path.join(d, filepath)
        with open(full_path, 'rb') as file:
            artifact = pickle.load(file)

    return artifact


def log_plots(run,
              study: optuna.Study,
              backend='plotly',
              log_plot_contour=True,
              log_plot_edf=True,
              log_plot_parallel_coordinate=True,
              log_plot_param_importances=True,
              log_plot_pareto_front=True,
              log_plot_slice=True,
              log_plot_intermediate_values=True,
              log_plot_optimization_history=True,
              ):
    if backend == 'matplotlib':
        import optuna.visualization.matplotlib as vis
    elif backend == 'plotly':
        import optuna.visualization as vis
    else:
        raise NotImplementedError(f'{backend} visualisation backend is not implemented')

    if vis.is_available:
        if log_plot_contour:
            run['visualizations/plot_contour'] = neptune.types.File.as_html(vis.plot_contour(study))
        if log_plot_edf:
            run['visualizations/plot_edf'] = neptune.types.File.as_html(vis.plot_edf(study))
        if log_plot_parallel_coordinate:
            run['visualizations/plot_parallel_coordinate'] = \
                neptune.types.File.as_html(vis.plot_parallel_coordinate(study))
        if log_plot_param_importances and len(study.trials) > 1:
            run['visualizations/plot_param_importances'] = neptune.types.File.as_html(vis.plot_param_importances(study))
        if log_plot_pareto_front and study._is_multi_objective() and backend == 'plotly':
            run['visualizations/plot_pareto_front'] = neptune.types.File.as_html(vis.plot_pareto_front(study))
        if log_plot_slice:
            run['visualizations/plot_slice'] = neptune.types.File.as_html(vis.plot_slice(study))
        if log_plot_intermediate_values and any(trial.intermediate_values for trial in study.trials):
            # Intermediate values plot if available only if the above condition is met
            run['visualizations/plot_intermediate_values'] = \
                neptune.types.File.as_html(vis.plot_intermediate_values(study))
        if log_plot_optimization_history:
            run['visualizations/plot_optimization_history'] = \
                neptune.types.File.as_html(vis.plot_optimization_history(study))


def log_best_trials(study: optuna.Study):
    best_results = {'value': study.best_value,
                    'params': study.best_params,
                    'value|params': f'value: {study.best_value}| params: {study.best_params}'}

    for trial in study.best_trials:
        best_results[f'trials/{trial._trial_id}/datetime_start'] = trial.datetime_start
        best_results[f'trials/{trial._trial_id}/datetime_complete'] = trial.datetime_complete
        best_results[f'trials/{trial._trial_id}/duration'] = trial.duration
        best_results[f'trials/{trial._trial_id}/distributions'] = trial.distributions
        best_results[f'trials/{trial._trial_id}/intermediate_values'] = trial.intermediate_values
        best_results[f'trials/{trial._trial_id}/params'] = trial.params
        best_results[f'trials/{trial._trial_id}/value'] = trial.value
        best_results[f'trials/{trial._trial_id}/values'] = trial.values

    return best_results


def log_all_trials(trials: Iterable[optuna.trial.FrozenTrial]):
    trials_results = {'values': [], 'params': [], 'values|params': []}
    for trial in trials:
        trials_results['values'].append(trial.value)
        trials_results['params'].append(trial.params)
        trials_results['values|params'].append(f'value: {trial.value}| params: {trial.params}')

        trials_results[f'trials/{trial._trial_id}/datetime_start'] = trial.datetime_start
        trials_results[f'trials/{trial._trial_id}/datetime_complete'] = trial.datetime_complete
        trials_results[f'trials/{trial._trial_id}/duration'] = trial.duration
        trials_results[f'trials/{trial._trial_id}/distributions'] = trial.distributions
        trials_results[f'trials/{trial._trial_id}/intermediate_values'] = trial.intermediate_values
        trials_results[f'trials/{trial._trial_id}/params'] = trial.params
        trials_results[f'trials/{trial._trial_id}/value'] = trial.value
        trials_results[f'trials/{trial._trial_id}/values'] = trial.values
    return trials_results


def log_study_metadata(study: optuna.Study,
                       run: neptune.Run,
                       base_namespace='',
                       should_log_plots=True,
                       should_log_study=True,
                       should_log_study_details=True,
                       should_log_best_trials=True,
                       should_log_all_trials=True,
                       should_log_distributions=True,
                       vis_backend='plotly',
                       log_plot_contour=True,
                       log_plot_edf=True,
                       log_plot_parallel_coordinate=True,
                       log_plot_param_importances=True,
                       log_plot_pareto_front=True,
                       log_plot_slice=True,
                       log_plot_intermediate_values=True,
                       log_plot_optimization_history=True):

    run = run[base_namespace]

    if should_log_all_trials:
        run['trials'] = stringify_keys(log_all_trials(study.trials))

    if should_log_distributions:
        run['study/distributions'].log(list(trial.distributions for trial in study.trials))

    if should_log_best_trials:
        run['best'] = stringify_keys(log_best_trials(study))

    if should_log_study_details:
        log_study_details(run, study)

    if should_log_plots:
        log_plots(run, study,
                  backend=vis_backend,
                  log_plot_contour=log_plot_contour,
                  log_plot_edf=log_plot_edf,
                  log_plot_parallel_coordinate=log_plot_parallel_coordinate,
                  log_plot_param_importances=log_plot_param_importances,
                  log_plot_pareto_front=log_plot_pareto_front,
                  log_plot_slice=log_plot_slice,
                  log_plot_optimization_history=log_plot_optimization_history,
                  log_plot_intermediate_values=log_plot_intermediate_values,
                  )

    if should_log_study:
        log_study(run, study)