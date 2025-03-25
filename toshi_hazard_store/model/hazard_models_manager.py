# import json
import logging

# from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from .hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig


class ManagerBase:
    def __init__(self, storage_folder: Path):
        self.storage_folder = storage_folder
        if not self.storage_folder.exists():
            self.storage_folder.mkdir(parents=True)

    def _get_path(self, unique_id: str) -> Path:
        raise NotImplementedError

    def create(self, data: Union[Dict, Any]) -> None:
        raise NotImplementedError

    def update(self, unique_id: str, data: Dict) -> None:
        raise NotImplementedError

    def delete(self, unique_id: str) -> None:
        path = self._get_path(unique_id)
        if path.exists():
            path.unlink()

    def get_all_ids(self) -> List[str]:
        return [p.stem for p in self.storage_folder.glob('*.json')]

    def load(self, unique_id: str) -> Any:
        raise NotImplementedError

    def _save_json(self, model: Any, file_path: Path):
        logging.info(f'saving model to {file_path}')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(model.model_dump_json())
            f.close()

    # def _load_json(self, file_path: Path) -> Union[CompatibleHazardCalculation, HazardCurveProducerConfig]:
    #     raise NotImplementedError


class CompatibleHazardCalculationManager(ManagerBase):
    Model = CompatibleHazardCalculation

    def __init__(self, storage_folder: Path):
        super().__init__(storage_folder / "compatible_hazard_calculations")

    def _get_path(self, unique_id: str) -> Path:
        return self.storage_folder / f"{unique_id}.json"

    def create(self, data: Union[Dict, CompatibleHazardCalculation]) -> None:
        if isinstance(data, dict):
            try:
                model = self.Model(**data)
            except ValidationError as e:
                raise ValueError(str(e))
        elif isinstance(data, self.Model):
            model = data
        else:
            raise TypeError("Data must be a dictionary or CompatibleHazardCalculation instance")

        path = self._get_path(model.unique_id)
        if path.exists():
            raise FileExistsError(f"Compatible Hazard Calculation with unique ID {model.unique_id} already exists.")

        self._save_json(model, path)

    def load(self, unique_id: str) -> CompatibleHazardCalculation:
        path = self._get_path(unique_id)
        if not path.exists():
            raise FileNotFoundError(f"Compatible Hazard Calculation with unique ID {unique_id} does not exist.")

        json_string = path.read_text()
        object = self.Model.model_validate_json(json_string)
        return object

    def update(self, unique_id: str, data: Dict) -> None:
        model = self.load(unique_id)
        for key, value in data.items():
            setattr(model, key, value)

        path = self._get_path(unique_id)
        self._save_json(model, path)


class HazardCurveProducerConfigManager(ManagerBase):
    Model = HazardCurveProducerConfig

    def __init__(self, storage_folder: Path, ch_manager: CompatibleHazardCalculationManager):
        super().__init__(storage_folder / "hazard_curve_producer_configs")
        self.ch_manager = ch_manager

    def _get_path(self, unique_id: str) -> Path:
        return self.storage_folder / f"{unique_id}.json"

    def create(self, data: Union[Dict, HazardCurveProducerConfig]) -> None:
        if isinstance(data, dict):
            try:
                model = self.Model(**data)
            except ValidationError as e:
                raise ValueError(str(e))
        elif isinstance(data, self.Model):
            model = data
        else:
            raise TypeError("Data must be a dictionary or HazardCurveProducerConfig instance")

        path = self._get_path(model.unique_id)
        if path.exists():
            raise FileExistsError(f"Hazard Curve Producer Config with unique ID {model.unique_id} already exists.")

        # Check referential integrity
        print(self.ch_manager.get_all_ids())
        print(model.compatible_calc_fk)
        if model.compatible_calc_fk not in self.ch_manager.get_all_ids():
            raise ValueError("Referenced compatible hazard calculation does not exist.")

        self._save_json(model, path)

    def load(self, unique_id: str) -> HazardCurveProducerConfig:
        path = self._get_path(unique_id)
        if not path.exists():
            raise FileNotFoundError(f"Hazard Curve Producer Config with unique ID {unique_id} does not exist.")

        json_string = path.read_text()
        object = HazardCurveProducerConfig.model_validate_json(json_string)
        return object

    def update(self, unique_id: str, data: Dict) -> None:
        model = self.load(unique_id)
        for key, value in data.items():
            setattr(model, key, value)

        # Check referential integrity
        ch_calc_manager = CompatibleHazardCalculationManager(self.storage_folder.parent)
        if 'compatible_calc_fk' in data and data['compatible_calc_fk'] not in ch_calc_manager.get_all_ids():
            raise ValueError("Referenced compatible hazard calculation does not exist.")

        path = self._get_path(unique_id)
        self._save_json(model, path)
