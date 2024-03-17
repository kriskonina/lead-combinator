import asyncio
import json
import pytest
from unittest.mock import ANY, AsyncMock, MagicMock
from datetime import datetime as dt

# from your_script import FileLogger, Status  # Adjust the import path as necessary
from unittest.mock import patch, mock_open

from back.app.services.krs import FileLogger, Status, process_response


class AsyncContextManagerMock:
    def __init__(self, mock_obj):
        self.mock_obj = mock_obj

    async def __aenter__(self):
        return self.mock_obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_file_logger_log():
    test_index = "123"
    test_status = Status.OK
    test_msg = "Test message"

    # Setup the mock for aiofiles.open correctly
    mock_file_handle = AsyncMock()
    with patch("aiofiles.open", AsyncMock(return_value=mock_file_handle)):
        logger = FileLogger("dummy.log")
        await logger.log(test_index, test_status, test_msg)

        # Ensure the mock aiofiles.open was awaited with the correct parameters
        mock_file_handle.write.assert_awaited_once_with(
            f"[{ANY}] - {test_index} - {test_status.value} - {test_msg}\n"
        )


# @pytest.mark.asyncio
# async def test_process_response_ok(mocker):
#     # Mock the session.get to return a successful response
#     mock_response = AsyncMock(
#         status=200,
#         text=AsyncMock(
#             return_value='{"odpis": {"naglowekP": {"wpis": [{"opis": "ACTIVE"}]}}}'
#         ),
#     )
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with("123", Status.OK)


# @pytest.mark.asyncio
# async def test_process_response_liquidation(mocker):
#     # Simulate a response indicating liquidation
#     mock_response_text = '{"odpis": {"naglowekP": {"wpis": [{"opis": "WYKREŚLENIE"}]}}}'
#     mock_response = AsyncMock(
#         status=200, text=AsyncMock(return_value=mock_response_text)
#     )
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with("123", Status.LIQ)


# @pytest.mark.asyncio
# async def test_process_response_not_found(mocker):
#     # Simulate a 404 Not Found response
#     mock_response = AsyncMock(status=404, text=AsyncMock(return_value="Not Found"))
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with("123", Status.NOT_FOUND)


# @pytest.mark.asyncio
# async def test_process_response_network_error(mocker):
#     # Simulate a network error
#     mock_session = AsyncMock(get=AsyncMock(side_effect=Exception("Network Error")))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with("123", Status.ERR, "Network Error")


# @pytest.mark.asyncio
# async def test_process_response_json_parsing_error(mocker):
#     # Simulate a JSON parsing error by returning invalid JSON
#     mock_response = AsyncMock(status=200, text=AsyncMock(return_value="{Invalid JSON"))
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with(
#         "123", Status.ERR, mocker.ANY
#     )  # Expecting a JSONDecodeError or similar


# @pytest.mark.asyncio
# async def test_process_response_unexpected_error(mocker):
#     # Simulate an unexpected error scenario
#     mock_session = AsyncMock(
#         get=AsyncMock(side_effect=RuntimeError("Unexpected Error"))
#     )
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with("123", Status.ERR, "Unexpected Error")


# @pytest.mark.asyncio
# async def test_process_response_data_structure_error(mocker):
#     # Simulate a response with an unexpected data structure
#     mock_response_text = '{"unexpected": "data"}'
#     mock_response = AsyncMock(
#         status=200, text=AsyncMock(return_value=mock_response_text)
#     )
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))
#     mock_logger = MagicMock(spec=FileLogger)

#     await process_response("123", mock_session, "P", "/tmp/dump", mock_logger)
#     mock_logger.log.assert_called_with(
#         "123", Status.ERR, mocker.ANY
#     )  # Expecting a KeyError or similar


# @pytest.mark.asyncio
# async def test_process_response_creates_correct_json_file(mocker):
#     # Setup: Mock the session.get to return a successful response with specific data
#     mock_data = {"odpis": {"naglowekP": {"wpis": [{"opis": "ACTIVE"}]}}}
#     mock_response_text = json.dumps(mock_data)
#     mock_response = AsyncMock(
#         status=200, text=AsyncMock(return_value=mock_response_text)
#     )
#     mock_session = AsyncMock(get=AsyncMock(return_value=mock_response))

#     # Mock aiofiles.open to intercept file writing
#     mock_aiofiles_open = mocker.patch("aiofiles.open", mocker.mock_open())

#     # Mock the logger to avoid actual file logging
#     mock_logger = MagicMock(spec=FileLogger)

#     # Define the index and dump path
#     test_index = "123"
#     dump_path = "/tmp/dump"

#     # Execute the function under test
#     await process_response(test_index, mock_session, "P", dump_path, mock_logger)

#     # Assert that the file was attempted to be opened with the correct path and mode
#     mock_aiofiles_open.assert_called_once_with(
#         f"{dump_path}/{test_index}.json", mode="w"
#     )

#     # Assert that the correct data was written to the file
#     # Since aiofiles.open is mocked, we access the mock's write call directly
#     handle = mock_aiofiles_open()
#     expected_write_data = json.dumps(
#         mock_data, ensure_ascii=False
#     ).encode()  # Adjust based on your actual serialization logic
#     handle.write.assert_awaited_once_with(expected_write_data)


# @pytest.mark.asyncio
# async def test_verify_post_run_integrity(mocker):
#     # Mock iglob to simulate existing JSON files
#     mocker.patch("glob.iglob", return_value=["/tmp/raw-500-600/500001.json"])

#     # Mock reading from a log file
#     mocker.patch(
#         "builtins.open", mocker.mock_open(read_data="[2024-03-17] - 500001 - OK - \n")
#     )

#     # Mock os.path and related calls if necessary
#     mocker.patch("os.path.exists", return_value=True)

#     # Your test logic here to call verify_post_run_integrity and assert the expected outcome
