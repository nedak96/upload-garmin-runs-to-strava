import logging
import os
import shutil
from datetime import datetime
from io import BufferedReader
from typing import Any, Dict, List
from zipfile import ZipFile

import constants
import garth

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class GarminActivity:
  activity_id: str

  def __init__(self, activity: Dict[str, Any]) -> None:
    self.activity_id = activity["activityId"]


class FitData:
  file_path: str
  file: BufferedReader

  def __init__(self, file_path) -> None:
    self.file_path = file_path

  def __enter__(self) -> BufferedReader:
    self.file = open(self.file_path, "rb")
    return self.file

  def __exit__(self, type, value, traceback) -> None:
    self.file.__exit__(type, value, traceback)
    os.remove(self.file_path)


class GarminClient:
  garth_client: garth.Client

  def __init__(self) -> None:
    self.garth_client = garth.Client()
    try:
      logger.info("Logging in with tokenfile")
      self.garth_client.load(constants.GARMIN_TOKEN_FILE_PATH)
    except Exception as e:
      logger.warning(
        "Error logging in with tokenfile, logging in with credentials: %s", e
      )
      self.garth_client.login(constants.GARMIN_USERNAME, constants.GARMIN_PASSWORD)
      self.garth_client.dump(constants.GARMIN_TOKEN_FILE_PATH)

  def get_activities(self) -> List[GarminActivity]:
    logger.info("Fetching activities from Garmin")
    try:
      activities = self.garth_client.connectapi(
        constants.GARMIN_ACTIVITIES_PATH,
        params={
          "startDate": datetime.today().strftime("%Y-%m-%d"),
          "activityType": "running",
        },
      )
    except Exception as e:
      logger.error("Error fetching activities from Garmin: %s", e)
      raise e

    return [GarminActivity(a) for a in activities]

  def get_fit_data(self, activityId) -> FitData:
    zip_file_path = f"{constants.DOWNLOAD_DIR}/{activityId}.zip"
    fit_file_path: str
    logger.info("Downloading activity from Garmin: %s", activityId)
    try:
      with self.garth_client.get(
        "connectapi",
        f"{constants.GARMIN_DOWNLOAD_FILES_PATH}/{activityId}",
        api=True,
        stream=True,
      ) as resp:
        logger.info("Save data to zip file: %s", activityId)
        with open(zip_file_path, "wb") as f:
          shutil.copyfileobj(resp.raw, f)
    except Exception as e:
      logger.error("Error fetching Garmin activity: %s", e)
      raise e

    logger.info("Extract zip data: %s", activityId)
    with ZipFile(zip_file_path) as zip:
      filename = zip.namelist()[0]
      fit_file_path = f"{constants.DOWNLOAD_DIR}/{filename}"
      zip.extract(filename, path=constants.DOWNLOAD_DIR)
    os.remove(zip_file_path)

    return FitData(fit_file_path)
