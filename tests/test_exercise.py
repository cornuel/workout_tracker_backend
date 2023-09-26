import os
import sys
import pytest
from unittest.mock import patch
from mongomock import MongoClient

# Add the project's root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import exercise.schema

from exercise.schema import Query
from exercise.models import Exercise, Poses

@pytest.fixture
def mock_exercises_collection():
    """
    A fixture that sets up a mock exercises collection for testing.

    return: The mock exercises collection.
    """
    # Set up mock data
    mock_client = MongoClient()
    mock_collection = mock_client.db.collection
    mock_exercises = [
        {"_id": "3", "name": "Exercise 3", "muscles": ["Muscle C", "Muscle D"]},
        {"_id": "2", "name": "Exercise 2", "muscles": ["Muscle C"]},
        {"_id": "1", "name": "Exercise 1", "muscles": ["Muscle A", "Muscle B"]}
    ]
    mock_collection.insert_many(mock_exercises)
    
    exercise.schema.exercises_collection = mock_collection

    yield mock_collection

    # Clean up mock data
    mock_collection.delete_many({})
    
@pytest.fixture
def mock_poses_collection():
    """
    A fixture that sets up a mock poses collection for testing.

    return: The mock poses collection.
    """
    # Set up mock data
    mock_client = MongoClient()
    mock_collection = mock_client.db.collection
    mock_poses = [
        {"_id": "1", "name": "Pose 1", "image": "image1"},
        {"_id": "2", "name": "Pose 2", "image": "image2"},
        {"_id": "3", "name": "Pose 3", "image": "image3"}
    ]
    mock_collection.insert_many(mock_poses)
    
    # Set the poses_collection attribute of the Query class
    exercise.schema.poses_collection = mock_collection

    yield mock_collection
    
    # Clean up mock data
    mock_collection.delete_many({})

class TestExerciseResolver:
    @pytest.mark.parametrize("muscles, expected_exercises", [
    # TEST CASE 1 - Return all exercises
    ([], [
        {"_id": "1", "name": "Exercise 1", "muscles": ["Muscle A", "Muscle B"]},
        {"_id": "2", "name": "Exercise 2", "muscles": ["Muscle C"]},
        {"_id": "3", "name": "Exercise 3", "muscles": ["Muscle C", "Muscle D"]}
    ]),
    # TEST CASE 2 - Return exercises matching a specific muscle
    (["Muscle C"], [
        {"_id": "2", "name": "Exercise 2", "muscles": ["Muscle C"]},
        {"_id": "3", "name": "Exercise 3", "muscles": ["Muscle C", "Muscle D"]}
    ]),
    # TEST CASE 3 - Return exercises matching more than one muscle
    (["Muscle C", "Muscle D"], [
        {"_id": "3", "name": "Exercise 3", "muscles": ["Muscle C", "Muscle D"]}
    ]),
    # TEST CASE 4 - Return no matching exercise
    (["Muscle E"], [])
])
    def test_resolve_all_exercises(self, mock_exercises_collection, muscles, expected_exercises):
        """
        Test the resolve_all_exercises method of the Query class.

        Parameters:
            mock_exercises_collection (fixture): The mocked exercises collection.
            muscles (list): A list of muscles to filter the exercises.
            expected_exercises (list): A list of expected exercises.

        Returns:
            None
        """

        # Create an instance of the Query class
        query = Query()
        
        # Set the exercises_collection to the mock_exercises_collection
        query.exercises_collection = mock_exercises_collection

        # Call the resolve_all_exercises method
        result = query.resolve_all_exercises(None, muscles)
        
        # Assert the results
        assert len(result) == len(expected_exercises)
        assert all(Exercise(**exercise) in result for exercise in expected_exercises)
            
    @pytest.mark.parametrize("expected_poses", [
        # TEST CASE 1 - Return all poses
        ([
            {"_id": "1", "name": "Pose 1", "image": "image1"},
            {"_id": "2", "name": "Pose 2", "image": "image2"},
            {"_id": "3", "name": "Pose 3", "image": "image3"}
        ])
    ])
    def test_resolve_all_poses(self, mock_poses_collection, expected_poses):
        """
        Test the resolve_all_poses method of the Query class.

        Parameters:
            mock_poses_collection (fixture): The mocked poses collection.

        Returns:
            None
        """
        # Create an instance of the Query class
        query = Query()

        # Set the poses_collection to the mock_poses_collection
        query.poses_collection = mock_poses_collection
        
        mock_poses = query.poses_collection

        # Call the resolve_all_poses method
        result = query.resolve_all_poses(None)
        
        # Assert the results
        assert len(result) == len(expected_poses)
        assert all(Poses(**pose) in result for pose in expected_poses)