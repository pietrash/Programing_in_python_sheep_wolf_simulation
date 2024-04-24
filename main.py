import argparse
import configparser
import csv
import json
import logging
import math
import os
import random
import sys

ALIVE_DIR = 'alive.csv'
POS_DIR = 'pos.json'
CHASE_DIR = 'chase.log'


class Animal:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Wolf(Animal):
    def move_towards(self, target_x, target_y, distance):
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x += distance * math.cos(angle)
        self.y += distance * math.sin(angle)


class Sheep(Animal):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.is_alive = True

    def move_randomly(self, distance):
        direction = random.choice(['north', 'south', 'east', 'west'])
        if direction == 'north':
            self.y += distance
        elif direction == 'south':
            self.y -= distance
        elif direction == 'east':
            self.x += distance
        elif direction == 'west':
            self.x -= distance
        return direction


def euclidean_distance(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def closest_sheep(wolf, sheep_list):
    min_distance = float('inf')
    closest = None

    for sheep in sheep_list:
        distance = euclidean_distance(wolf.x, wolf.y, sheep.x, sheep.y)
        if distance < min_distance and sheep.is_alive:
            min_distance = distance
            closest = sheep

    return closest


def save_to_json(round_num, wolf, sheep_list):
    # Read existing data
    try:
        with open(POS_DIR, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = []

    # Add new data to existing data
    new_data = {
        'round_no': round_num,
        'wolf_pos': {'x': round(wolf.x, 3), 'y': round(wolf.y, 3)},
        'sheep_pos': [{'x': round(s.x, 3), 'y': round(s.y, 3)} if s.is_alive else None for s in sheep_list]
    }
    existing_data.append(new_data)

    # Write updated data to the file
    with open(POS_DIR, 'w') as file:
        json.dump(existing_data, file, indent=2)

    logging.debug("Data saved to pos.json")


def save_to_csv(round_num, num_alive_sheep):
    # Read existing data
    try:
        with open(ALIVE_DIR, 'r', newline='') as file:
            existing_data = list(csv.reader(file))
    except FileNotFoundError:
        existing_data = []

    # Add new data to existing data
    new_data = [round_num, num_alive_sheep]
    existing_data.append(new_data)

    # Write updated data to the file
    with open(ALIVE_DIR, 'w', newline='') as file:
        csv.writer(file).writerows(existing_data)

    logging.debug("Data saved to alive.csv")


def setup_logging(log_level):
    logging.basicConfig(filename=CHASE_DIR, level=log_level, format='%(levelname)s: %(message)s')
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def setup_parser():
    parser = argparse.ArgumentParser(description='Wolf and Sheep Simulation', conflict_handler='resolve')
    parser.add_argument('-c', '--config', type=str, help='Configuration file')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    parser.add_argument('-l', '--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level')
    parser.add_argument('-r', '--rounds', type=int, help='Maximum number of rounds')
    parser.add_argument('-s', '--sheep', type=int, help='Number of sheep')
    parser.add_argument('-w', '--wait', action='store_true', help='Introduce a pause at the end of each round')

    return parser


def delete_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def main():
    delete_file(ALIVE_DIR)
    delete_file(POS_DIR)
    delete_file(CHASE_DIR)

    parser = setup_parser()
    args = parser.parse_args()

    if args.help:
        parser.print_help()
        sys.exit()

    if args.log:
        log_level = getattr(logging, args.log)
        setup_logging(log_level)

    if args.config:
        if not os.path.exists(args.config):
            logging.critical("Config file does not exist")
            sys.exit()

        config = configparser.ConfigParser()
        config.read(args.config)
        init_pos_limit = float(config.get('Sheep', 'InitPosLimit'))
        move_dist_sheep = float(config.get('Sheep', 'MoveDist'))
        move_dist_wolf = float(config.get('Wolf', 'MoveDist'))

        if init_pos_limit < 0:
            logging.critical(f"Invalid initial position value, must be grater or equal 0")
            sys.exit()
        if move_dist_sheep < 0:
            logging.critical(f"Invalid sheep move distance value, must be grater or equal 0")
            sys.exit()
        if move_dist_wolf <= 0:
            logging.critical(f"Invalid wolf move distance value, must be grater than 0")
            sys.exit()

        logging.debug("Configuration file loaded")
        logging.debug(f"Initial position limit: {init_pos_limit}")
        logging.debug(f"Sheep move distance: {move_dist_sheep}")
        logging.debug(f"Wolf move distance: {move_dist_wolf}")
    else:
        init_pos_limit = 10.0
        move_dist_sheep = 0.5
        move_dist_wolf = 1.0

    if args.rounds:
        max_rounds = args.rounds
        if max_rounds <= 0:
            logging.critical(f"Invalid max rounds value, must be grater than 0")
            sys.exit()
    else:
        max_rounds = 50

    if args.sheep:
        num_sheep = args.sheep
        if num_sheep <= 0:
            logging.critical(f"Invalid sheep number value, must be grater than 0")
            sys.exit()
    else:
        num_sheep = 15

    num_alive_sheep = num_sheep
    sheep_list = [Sheep(random.uniform(-init_pos_limit, init_pos_limit),
                        random.uniform(-init_pos_limit, init_pos_limit)) for _ in range(num_sheep)]
    wolf = Wolf(0.0, 0.0)

    # Log initial position of sheep
    logging.info("Initialized sheep positions")
    for sheep in sheep_list:
        logging.debug(f"Sheep {sheep_list.index(sheep)} initial position ({round(sheep.x, 3)}, {round(sheep.y, 3)})")

    for round_num in range(1, max_rounds + 1):
        if num_alive_sheep == 0:
            logging.info("All sheep have been eaten. Simulation over.")
            break

        logging.info(f"Starting round {round_num}")

        # Move all sheep randomly
        for sheep in sheep_list:
            if sheep.is_alive:
                direction = sheep.move_randomly(move_dist_sheep)
                logging.info(f"Sheep {sheep_list.index(sheep)} moved")
                logging.debug(f"Sheep {sheep_list.index(sheep)} moved {direction} "
                              f"to ({round(sheep.x, 3)}, {round(sheep.y, 3)})")

        # Find the closest sheep
        closest = closest_sheep(wolf, sheep_list)

        # Kill the closest sheep
        distance = euclidean_distance(wolf.x, wolf.y, closest.x, closest.y)
        logging.debug(f"Sheep {sheep_list.index(closest)} is closest to the wolf, distance: {round(distance, 3)}")
        if closest and distance <= move_dist_wolf:
            closest.is_alive = False
            wolf.x = closest.x
            wolf.y = closest.y

            num_alive_sheep -= 1

            logging.info(f"Wolf caught a sheep {sheep_list.index(closest)}")

        # Move towards the closest sheep
        else:
            wolf.move_towards(closest.x, closest.y, move_dist_wolf)
            logging.info(f"Wolf chasing sheep {sheep_list.index(closest)}")

        logging.info("Wolf moved")
        logging.debug(f"Wolf moved, position: ({wolf.x:.3f}, {wolf.y:.3f})")
        logging.info(f"Number of alive sheep: {num_alive_sheep}")
        logging.info("Round complete")

        # Save round data
        save_to_json(round_num, wolf, sheep_list)
        save_to_csv(round_num, num_alive_sheep)

        if args.wait:
            input("Press Enter to continue to the next round...")

    if num_alive_sheep != 0:
        logging.info("Maximum rounds reached. Simulation over.")


if __name__ == "__main__":
    main()
