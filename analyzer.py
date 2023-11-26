import json
import logging
import os

# Setup logger for the application
log_file = 'analyzer.log'
logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# File Reader Module
def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        raise

def read_objects_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.readlines()
    except Exception as e:
        logger.error(f"Error reading objects file {file_path}: {e}")
        raise

# Data Analysis Module
import re

def extract_data_from_objects(lines):
    data = []
    current_patrol_path = None
    model_id_regex = r"\d{3}_\d{2}_\d"

    for line in lines:
        if "Task_New" in line:
            line_parts = line.split(',')
            task_id = line_parts[0].split('(')[1].strip()
            #logger.info(f"Found new task: {task_id}")

            if "PatrolPath" in line:
                logger.info(f"line is {line}")
                current_patrol_path = {'patrol_path_id': task_id, 'commands': [], 'soldiers': [], 'ai': []}
                data.append(current_patrol_path)
                logger.info(f"Found new patrol path: {current_patrol_path}")
            elif "PatrolPathCommand" in line and current_patrol_path is not None:
                command_note = line_parts[2].strip('" ')
                command_id = line_parts[3].strip()
                command_param = line_parts[4].split(')')[0].strip()
                logger.info(f"Found new command: {command_note} (Command Id {command_id}, Parameter: {command_param})")
                current_patrol_path['commands'].append({'note': command_note, 'id': command_id, 'param': command_param})
                logger.info(f"Added command to patrol path: {current_patrol_path['commands'][-1]}")
            elif "HumanSoldier" in line and current_patrol_path is not None:
                model_id_search = re.search(model_id_regex, line)
                if model_id_search:
                    model_id = model_id_search.group()
                    current_patrol_path['soldiers'].append({'soldier_id': task_id, 'model_id': model_id})
                    logger.info(f"Added soldier to patrol path: {current_patrol_path['soldiers'][-1]}")
            elif "HumanAI" in line and current_patrol_path is not None:
                ai_type = line_parts[3].strip('" ')
                graph_id = line_parts[4].split(')')[0].strip()
                current_patrol_path['ai'].append({'ai_id': task_id, 'ai_type': ai_type, 'graph_id': graph_id})
                logger.info(f"Added AI to patrol path: {current_patrol_path['ai'][-1]}")
    
    return data



# Report Generator Module
def generate_report(data, ai_models, graph_areas):
    report = ""
    command_meanings = {
        '0': 'Animation',
        '1': 'Delay',
        '2': 'Walk to',
        '3': 'Run to',
        '4': 'Crouch',
        '5': 'Look at node',
        '6': 'End',
        '7': 'Quit',
        '8': 'Set speed'
    }

    for item in data:
        logger.info(f"Processing item: {item}")
        logger.info(f"Processing patrol path {item['patrol_path_id']}")
        patrol_path_id = item['patrol_path_id']
        logger.info(f"Processing id {patrol_path_id}")
        
        commands_report = []
        for command in item['commands']:
            command_note = command['note']
            command_id = command['id']
            command_meaning = command_meanings.get(command_id, 'Unknown')
            command_param = command['param']
            commands_report.append(f"{command_note} (Command Id {command_id}: {command_meaning}, Parameter: {command_param})")
        commands_str = ", ".join(commands_report)

        for soldier in item['soldiers']:
            soldier_id = soldier['soldier_id']
            model_id = soldier['model_id']
            soldier_name = next((model['ModelName'] for model in ai_models if model['ModelId'] == model_id), "Unknown")
            report += f"Soldier {soldier_id} '{soldier_name}' is executing patrol path {patrol_path_id} with commands: {commands_str}.\n"

        for ai in item['ai']:
            ai_id = ai['ai_id']
            ai_type = ai['ai_type']
            graph_id = ai['graph_id']
            graph_name = next((area['Area'] for area in graph_areas if area['Graph'] == f"Graph #{graph_id}"), "Unknown Area")
            report += f"AI {ai_id} {ai_type} is in the graph area: {graph_name}.\n"

    return report



# User Interaction Module
def get_user_input():
    try:
        level = int(input("Enter the game level: "))
        if level < 1 or level > 14:
            logger.error("Please enter a valid level between 1 and 14.")
            raise Exception("Invalid level entered.")
        return level
    except Exception as e:
        logger.error(f"Error in getting user input: {e}")
        raise

# Main function to orchestrate the script
def main():
    try:
        level = get_user_input()
        curr_path = os.path.dirname(os.path.realpath(__file__))
        missions_path = curr_path + f"/missions/location0/level{level}/objects.qsc"
        ai_path = curr_path + f"/location0/level{level}/ai/"
        graph_area_path = curr_path + f"/GraphAreas/graph_area_level{level}.json"
        
        # Read and process files
        objects_lines = read_objects_file(missions_path)
        ai_models = read_json_file("AI-Models.json")
        graph_areas = read_json_file(graph_area_path)

        # Extract and analyze data
        extracted_data = extract_data_from_objects(objects_lines)

        # Generate and display the report
        report = generate_report(extracted_data, ai_models, graph_areas)
        print(report)

    except Exception as exception:
        # print stack trace
        import traceback
        traceback.print_exc()
        logger.error(f"An error occurred in the main function: {exception}")

if __name__ == "__main__":
    main()
