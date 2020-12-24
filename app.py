# -*- coding: utf-8 -*-
# Copyright (c) 2019 Linh Pham
# wwdtm_scoreimage is relased under the terms of the Apache License 2.0
"""Generate PNG image file based on WWDTM show score totals"""

import json
import math
import os
from typing import List
import mysql.connector
from mysql.connector.errors import DatabaseError, ProgrammingError
import numpy
from PIL import Image

BASE_IMAGE_WIDTH = 30
IMAGE_SCALE = 40

def retrieve_show_total_scores(database_connection: mysql.connector) -> List[int]:
    """Retrieve total scores for each show"""
    cursor = database_connection.cursor()
    query = ("select sum(pm.panelistscore) as total "
             "from ww_showpnlmap pm "
             "join ww_shows s on s.showid = pm.showid "
             "where s.bestof = 0 and s.repeatshowid is null "
             "group by s.showdate "
             "having sum(pm.panelistscore) > 0")
    cursor.execute(query)
    result = cursor.fetchall()

    if not result:
        return None

    scores = []
    for row in result:
        scores.append(int(row[0]))

    return scores

def remap(in_value: int,
          in_minimum: int,
          in_maximum: int,
          out_minimum: int,
          out_maximum: int) -> int:
    """Remap a value from one value range to another value range
    while maintaining ratio"""
    new_value = (in_value - in_minimum) * (out_maximum - out_minimum) \
                / (in_maximum - in_minimum) + out_minimum
    return math.floor(new_value)

def pad(list_object: List, content, width: int) -> List:
    list_object.extend([content] * (width - len(list_object)))
    return list_object

def split(values):
    for i in range(0, len(values), BASE_IMAGE_WIDTH):
        yield values[i:i+BASE_IMAGE_WIDTH]

def convert_list_to_pixels(values: List[int]) -> List[List]:
    pixels = []
    for row in values:
        row_tuples = []
        for value in row:
            row_tuples.append((value, math.floor(value / 3), 0))

        if len(row_tuples) < BASE_IMAGE_WIDTH:
            pad(row_tuples, (0, 0, 0), BASE_IMAGE_WIDTH)

        pixels.append(row_tuples)

    return pixels

def generate_image(values, dimension_side: int):
    """Generate a PNG image based on a list of integers"""
    image_size = dimension_side * IMAGE_SCALE
    array = numpy.array(values, dtype=numpy.uint8)
    image = Image.fromarray(array)
    resized_image = image.resize((image_size, image_size), Image.NEAREST)
    resized_image.save('output.png')
    resized_image.show()

def load_config(app_environment):
    """Load configuration file from config.json"""
    with open('config.json', 'r') as config_file:
        config_dict = json.load(config_file)

    if app_environment.startswith("develop"):
        if "development" in config_dict:
            config = config_dict["development"]
        else:
            raise Exception("Missing 'development' section in config file")
    elif app_environment.startswith("prod"):
        if "production" in config_dict:
            config = config_dict['production']
        else:
            raise Exception("Missing 'production' section in config file")
    else:
        if "local" in config_dict:
            config = config_dict["local"]
        else:
            raise Exception("Missing 'local' section in config file")

    return config

def main():
    """Pull in scoring data and generate image based on the data"""
    app_environment = os.getenv("APP_ENV", "local").strip().lower()
    config = load_config(app_environment)
    database_connection = mysql.connector.connect(**config["database"])
    original_totals = retrieve_show_total_scores(database_connection)

    if not original_totals:
        print("No scores to process")

    original_min_total = min(original_totals)
    original_max_total = max(original_totals)

    new_min_value = 0
    new_max_value = 255
    remapped_totals = []

    for total in original_totals:
        remapped_totals.append(remap(total,
                                     original_min_total,
                                     original_max_total,
                                     new_min_value,
                                     new_max_value))

    list_values = list(split(remapped_totals))
    pixels = list(convert_list_to_pixels(list_values))
    side = math.ceil(math.sqrt(len(original_totals)))
    generate_image(pixels, side)

# Only run if executed as a script and not imported
if __name__ == '__main__':
    main()
