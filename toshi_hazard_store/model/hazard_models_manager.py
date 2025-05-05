"""This module provide classes for managing hazard models as json files.

It is used for local storage of these small and slow moving artefacts.

Each manager class will store a canonical list of instance 'unique_id`s and will
 provide methods for creating, updating and deleting instances, with
 serialisation to/from json.

Note:
 - CLI scripts will use these classes to maintain the metadata for published datasets.

Classes:
  - CompatibleHazardCalculationManager
  - HazardCurveProducerConfigManager
 """

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

from pydantic import ValidationError

from toshi_hazard_store.model.hazard_models_pydantic import CompatibleHazardCalculation, HazardCurveProducerConfig


class ManagerBase:
    """Base class for managing storage of object models.

    Attributes:
        storage_folder: The directory where objects are stored as JSON files.
    """

    def __init__(self, storage_folder: Path):
        """Initialize the manager with a specified storage folder."""
        self.storage_folder = storage_folder

        if not storage_folder.parent.is_dir():
            raise ValueError(f"'{storage_folder.parent}' is not a valid path for storage_folder.")

        if not self.storage_folder.exists():
            self.storage_folder.mkdir(parents=False)

    def _get_path(self, unique_id: str) -> Path:
        """Generate the file path for a given object ID.

        Args:
            unique_id: The unique identifier of the object.

        Returns:
            A Path object pointing to the JSON file.
        """
        raise NotImplementedError

    def create(self, data: Union[Dict, Any]) -> None:
        """Create and save a new object from provided data.

        Args:
            data: object parameters as a dictionary or model instance.

        Raises:
            ValueError: If validation of input data fails.
            FileExistsError: If the ID already exists in storage.
        """
        raise NotImplementedError

    def update(self, unique_id: str, data: Dict) -> None:
        """Update an existing object with new parameters.

        Args:
            unique_id: The identifier of the object to modify.
            data: New parameters for the object.

        Raises:
            FileNotFoundError: If the ID does not exist in storage.
        """
        raise NotImplementedError

    def delete(self, unique_id: str) -> None:
        """Remove a object from storage by its ID.

        Args:
            unique_id: The identifier of the object to delete.
        """
        path = self._get_path(unique_id)
        if path.exists():
            path.unlink()

    def get_all_ids(self) -> List[str]:
        """Retrieve all IDs of objects stored in the folder.

        Returns:
            A list of string identifiers for existing objects.
        """
        return [p.stem for p in self.storage_folder.glob('*.json')]

    def load(self, unique_id: str) -> Any:
        """Load a object from storage by its ID.

        Args:
            unique_id: The identifier of the object to retrieve.

        Returns:
            The loaded object model instance.

        Raises:
            FileNotFoundError: If no object exists with that ID.
        """
        raise NotImplementedError

    def _save_json(self, model: Any, file_path: Path):
        """Serialize a Pydantic model to JSON and save it to disk.

        Args:
            model: The object model to persist.
            file_path: Target path for the JSON file.
        """
        logging.info(f'saving model to {file_path}')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(model.model_dump_json(indent=2))
            f.close()


class CompatibleHazardCalculationManager(ManagerBase):
    """Manager for handling compatible hazard calculations.

    Attributes:
        storage_folder: Directory where calculation objects are stored.
    """

    def __init__(self, storage_folder: Path):
        super().__init__(storage_folder / "compatible_hazard_calculations")

    def _get_path(self, unique_id: str) -> Path:
        """Override to generate paths for compatible hazard calculations."""
        return self.storage_folder / f"{unique_id}.json"

    def create(self, data: Union[Dict, CompatibleHazardCalculation]) -> None:
        """Create a new compatible hazard calculation object.

        Args:
            data: Input parameters as dictionary or model instance.

        Raises:
            TypeError: If input is not valid type.
            FileExistsError: When duplicate ID already exists.
        """
        if isinstance(data, dict):
            try:
                model = CompatibleHazardCalculation(**data)
            except ValidationError as e:
                raise ValueError(str(e))
        elif isinstance(data, CompatibleHazardCalculation):
            model = data
        else:
            raise TypeError("Data must be a dictionary or CompatibleHazardCalculation instance")

        path = self._get_path(model.unique_id)
        if path.exists():
            raise FileExistsError(f"Compatible Hazard Calculation with unique ID {model.unique_id} already exists.")

        self._save_json(model, path)

    def load(self, unique_id: str) -> CompatibleHazardCalculation:
        """Load a compatible hazard calculation object by ID.

        Args:
            unique_id: The identifier of the object to retrieve.

        Returns:
            The loaded object model instance.
        """
        path = self._get_path(unique_id)
        if not path.exists():
            raise FileNotFoundError(f"Compatible Hazard Calculation with unique ID {unique_id} does not exist.")

        json_string = path.read_text()
        return CompatibleHazardCalculation.model_validate_json(json_string)

    def update(self, unique_id: str, data: Dict) -> None:
        """Update an existing compatible hazard calculation object.

        Args:
            unique_id: object ID to modify.
            data: New parameters for the object.
        """
        model = self.load(unique_id)
        for key, value in data.items():
            setattr(model, key, value)
        if 'updated_at' not in data.keys():
            setattr(model, 'updated_at', datetime.now(timezone.utc))

        path = self._get_path(unique_id)
        self._save_json(model, path)


class HazardCurveProducerConfigManager(ManagerBase):
    """Manager for hazard curve producer objects.

    Attributes:
        storage_folder: Directory where object files are stored.
        ch_manager: Reference to compatible calculation manager for integrity checks.
    """

    def __init__(self, storage_folder: Path, ch_manager: CompatibleHazardCalculationManager):
        super().__init__(storage_folder / "hazard_curve_producer_configs")
        self.ch_manager = ch_manager

    def _get_path(self, unique_id: Union[Callable, str]) -> Path:
        """Override path generation for hazard curve producer objects."""
        return self.storage_folder / f"{unique_id}.json"

    def create(self, data: Union[Dict, HazardCurveProducerConfig]) -> None:
        """Create a new hazard curve producer object.

        Args:
            data: Input parameters as dictionary or model instance.

        Raises:
            ValueError: If validation fails or referenced calculation doesn't exist.
            FileExistsError: When duplicate ID already exists.
        """
        if isinstance(data, dict):
            try:
                model = HazardCurveProducerConfig(**data)
            except ValidationError as e:
                raise ValueError(str(e))
        elif isinstance(data, HazardCurveProducerConfig):
            model = data
        else:
            raise TypeError("Data must be a dictionary or HazardCurveProducerConfig instance")

        path = self._get_path(model.unique_id)
        if path.exists():
            raise FileExistsError(f"Hazard Curve Producer Config with unique ID {model.unique_id} already exists.")

        # Check referential integrity
        if model.compatible_calc_fk not in self.ch_manager.get_all_ids():
            raise ValueError(f"Referenced compatible hazard calculation {model.compatible_calc_fk} does not exist.")

        self._save_json(model, path)

    def load(self, unique_id: Union[Callable, str]) -> HazardCurveProducerConfig:
        """Load a hazard curve producer object by ID.

        Args:
            unique_id: The identifier of the object to retrieve.

        Returns:
            The loaded object model instance.

        Raises:
            ValueError: If referenced compatible hazard calculation doesn't exist.
        """
        path = self._get_path(unique_id)
        if not path.exists():
            raise FileNotFoundError(f"Hazard Curve Producer Config with unique ID {unique_id} does not exist.")

        json_string = path.read_text()
        model = HazardCurveProducerConfig.model_validate_json(json_string)

        # Check referential integrity
        if model.compatible_calc_fk not in self.ch_manager.get_all_ids():
            raise ValueError(f"Referenced compatible hazard calculation {model.compatible_calc_fk} does not exist.")
        return model

    def update(self, unique_id: Union[Callable, str], data: Dict) -> None:
        """Update an existing hazard curve producer object.

        Args:
            unique_id: object ID to modify.
            data: New parameters for the object.

        Raises:
            ValueError: If referenced compatible hazard calculation doesn't exist (save precondition).
        """
        model = self.load(unique_id)
        for key, value in data.items():
            setattr(model, key, value)
        if 'updated_at' not in data.keys():
            setattr(model, 'updated_at', datetime.now(timezone.utc))

        # Check referential integrity
        if 'compatible_calc_fk' in data and data['compatible_calc_fk'] not in self.ch_manager.get_all_ids():
            raise ValueError(f"Referenced compatible hazard calculation {data['compatible_calc_fk']} does not exist.")

        path = self._get_path(unique_id)
        self._save_json(model, path)
