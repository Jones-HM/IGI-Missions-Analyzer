"""
Brief: This script analyzes the missions files and generates a report of the AI activity.
Game : Project IGI
Author: HeavenHM
Date: 2023-11-26
"""
import json
import logging
import os
import re


# Setup logger
def setup_logger(log_file):
    """Function setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

# setup logger
logger = setup_logger('mission_analyzer.log')

# File Reader Module
def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as exception:
        logger.error(f"Error reading JSON file {file_path}: {exception}")
        raise

def read_objects_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.readlines()
        
    except Exception as exception:
        logger.error(f"Error reading objects file {file_path}: {exception}")
        raise

def strip_quotes_and_whitespace(text):
    """Utility function to strip quotes and whitespace from a string."""
    return text.strip().strip('"')

def process_patrol_path(task_id, line_parts, patrol_paths):
    """Process patrol path task."""
    patrol_paths[task_id] = {'commands': [], 'soldiers': [], 'ai': {}}
    logger.info(f"Found new patrol path: {task_id}")

def process_patrol_path_command(task_id, line_parts, patrol_paths):
    """Process patrol path command task."""
    command_note = strip_quotes_and_whitespace(line_parts[2])
    command_action = line_parts[3].strip()
    command_param = line_parts[4].split(')')[0].strip()
    patrol_paths[task_id]['commands'].append({'note': command_note, 'action': command_action, 'param': command_param})
    logger.info(f"Found new command: {command_note} (Command Action {command_action}, Parameter: {command_param})")

def process_human_soldier(task_id, line, model_id_regex, patrol_paths):
    """Process human soldier task."""
    model_id_search = re.search(model_id_regex, line)
    if model_id_search:
        model_id = model_id_search.group()
        logger.info(f"Found new soldier: {model_id}")
        if task_id in patrol_paths:
            patrol_paths[task_id]['soldiers'].append({'soldier_id': task_id, 'model_id': model_id})

def process_human_ai(task_id, line_parts, patrol_paths,graph_area_path):
    """Process human AI task."""
    logger.error(f"Processing human AI task with arguements {task_id} and {line_parts} and {patrol_paths} and {graph_area_path}")
    ai_type = line_parts[3].strip('" ')
    graph_id = int(line_parts[4].split(')')[0].strip())
    if graph_id <= 0:
        logger.warning(f"AI with task ID {task_id} has graph ID 0. Skipping...")
        return
    
    graph_area = get_area_by_graph_id(graph_id, graph_area_path)
    if task_id in patrol_paths:
        patrol_paths[task_id]['ai'] = {'ai_id': task_id, 'ai_type': ai_type,'graph_id':graph_id, 'graph_area': graph_area}
        logger.info(f"Found new AI: {ai_type} Graph ID '{graph_id}'")

def link_ai_to_patrol_paths(patrol_paths, ai_path):
    ai_files = [f for f in os.listdir(ai_path) if f.endswith('.qsc')]
    logger.info(f"Found {len(ai_files)} AI files in {ai_path}")
    for ai_file in ai_files:
        ai_file_path = os.path.join(ai_path, ai_file)
        with open(ai_file_path, 'r') as file:
            ai_lines = file.readlines()
        for line in ai_lines:
            if "AIAction_Patrol" in line:
                patrol_id = re.findall(r"\d+", line)[0]
                ai_id = ai_file.split('.')[0]
                if patrol_id in patrol_paths:
                    patrol_paths[patrol_id]['ai_id'] = ai_id
                    logger.info(f"Linked AI ID {ai_id} to patrol path with task ID: {patrol_id}")

def generate_json_and_report(patrol_paths, graph_area_path, ai_path, level):
    graph_areas = read_json_file(graph_area_path)

    for path_id, path_data in patrol_paths.items():
        if 'ai_id' in path_data:
            ai_file = f"{path_data['ai_id']}.qsc"
            ai_lines = read_objects_file(os.path.join(ai_path, ai_file))
            for line in ai_lines:
                if line.startswith(f"Task_New({path_data['ai_id']},"):
                    ai_type_match = re.search(r'"(AITYPE_[\w]+)"', line)
                    graph_id_match = re.search(r"Graph #(\d+)", line)
                    if ai_type_match:
                        path_data['ai_type'] = ai_type_match.group(1)
                        logger.info(f"Found AI type '{path_data['ai_type']}' for AI ID: {path_data['ai_id']}")
                    if graph_id_match:
                        graph_id = line[4].split(')')[0].strip()
                        path_data['graph_area'] = next((area['Area'] for area in graph_areas if area['Graph'] == f"Graph #{graph_id}"), "Unknown Area")
                        logger.info(f"Found graph area '{path_data['graph_area']}' for AI ID: {path_data['ai_id']}")

    json_data = json.dumps(patrol_paths, indent=4)
    json_file_name = f"level{level}_ai_mission.json"
    with open(json_file_name, 'w') as json_file:
        json_file.write(json_data)

    report = create_report_from_data(patrol_paths)
    return report

def extract_patrol_path_data(lines,graph_area_path):
    patrol_paths = {}
    model_id_regex = r"\d{3}_\d{2}_\d"
    model_id_pattern = re.compile(model_id_regex)
    patrol_path_id = 0
    
    for line in lines:
        try:
            line = line.strip()
            if "Task_New" in line:
                line_parts = line.split(',')
                task_id = line_parts[0].split('(')[1].strip()
                task_type = strip_quotes_and_whitespace(line_parts[1])

                if task_type == "PatrolPath":
                    process_patrol_path(task_id, line_parts, patrol_paths)
                    patrol_path_id = task_id
                elif task_type == "PatrolPathCommand" and patrol_path_id in patrol_paths:
                    process_patrol_path_command(patrol_path_id, line_parts, patrol_paths)
                elif task_type == "HumanSoldier" and patrol_path_id in patrol_paths:
                    process_human_soldier(patrol_path_id, line, model_id_pattern, patrol_paths)
                elif task_type == "HumanAI" and patrol_path_id in patrol_paths:
                    process_human_ai(patrol_path_id, line_parts, patrol_paths,graph_area_path)
        except Exception as exception:
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"Error processing line: {line}. Error: {exception}")

    return patrol_paths

def get_area_by_graph_id(graph_id, file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        
    for item in data:
        if int(item['Graph'].split('#')[1]) == graph_id:
            return item['Area']
    
    return None

def summarize_soldier_activity(actions):
    action_messages = {
        "walks to": "Soldier is walking. 🚶",
        "runs to": "Soldier is running. 🏃",
        "looks at": "Soldier is looking at a node. 👀",
        "delays the script execution for": "Soldier is delayed. ⏳",
        "end script": "Soldier is ending the script. 🛑",
        "plays predefined animation": "Soldier is playing an animation. 🕺",
        "crouching down": "Soldier is crouching. 🚶‍♂️",
        "quit script": "Soldier is quitting the script. 🚫"
    }

    lines = actions.split('\n')
    summary = """
       Soldier Activity Summary
---------------------------------\n\n"""

    for line in lines:
        for action_keyword, message in action_messages.items():
            if action_keyword in line.lower():
                summary += f"{message} ({line})\n"
                break
        else:
            summary += "Unknown action\n"

    return summary


def create_report_from_data(patrol_paths):
    report = "\n\n"

    for path_id, path_data in patrol_paths.items():
        if 'ai_id' in path_data:
            ai_type = path_data['ai'].get('ai_type', 'Not Specified')
            if ai_type != 'Not Specified':
                ai_type = ai_type.replace('AITYPE_', '')
                
            graph_id = path_data['ai'].get('graph_id', 'Not Specified')
            graph_area = path_data['ai'].get('graph_area', 'Not Specified')
            commands = path_data['commands']
            
            ai_not_found = ai_type == graph_id == graph_area == 'Not Specified'
            if ai_not_found:
                logger.warning(f"AI not found for patrol path {path_id}. Skipping...")
                continue
            
            notes = "\n".join(command['note'] for command in commands) if commands else "No Commands"
            
            report += f"{ai_type} ({path_data['ai_id']}) on Patrol ({path_id}) with Graph ({graph_id}) ({graph_area})\n"
            report += summarize_soldier_activity(notes) + "\n\n"

    return report + "\n\n"


# Main function to orchestrate the script
def main():
    try:
        # Read the level number from the user
        print("Project IGI- Missions Analyzer")
        level = int(input("Enter the level: "))
        
        if level < 1 or level > 14:
            raise ValueError("Level number must be between 1 and 14")
        
        curr_path = os.path.dirname(os.path.realpath(__file__))
        missions_path = os.path.join(curr_path, f"missions/location0/level{level}/objects.qsc")
        ai_path = os.path.join(curr_path, f"missions/location0/level{level}/ai/")
        graph_area_path = os.path.join(curr_path, f"GraphAreas/graph_area_level{level}.json")

        # Read and process files
        logger.info(f"Reading missions file from {missions_path}")
        logger.info(f"Reading AI files from {ai_path}")
        logger.info(f"Reading graph area file from {graph_area_path}")

        objects_lines = read_objects_file(missions_path)
        patrol_paths = extract_patrol_path_data(objects_lines,graph_area_path)
        link_ai_to_patrol_paths(patrol_paths, ai_path)
        report = generate_json_and_report(patrol_paths, graph_area_path, ai_path, level)
        # move the report to the reports folder
        
        report_file_name = f"level{level}_ai_mission_report.json"
        with open(report_file_name, 'w') as report_file:
            report_file.write(report)
            # check if file report exists
            if os.path.exists(report_file_name):
                # move the file to reports folder
                os.replace(report_file_name, f"reports/{report_file_name}")
                logger.info(f"Report file {report_file_name} moved to reports folder")
            else:
                logger.error(f"Report file {report_file_name} not found")

    except Exception as exception:
        # print the stack trace
        import traceback
        logger.error(traceback.format_exc())
        logger.error(f"An error occurred: {exception}")
        raise

if __name__ == "__main__":
    main()
