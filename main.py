import os
import argparse
import logging
import sys
from cli.cli import interactive_cli
from plm.plm import ProjectLifecycleManager
from ppe.ppe import PreprocessorEngine
from ae.ae import AnalysisEngine
from reporting_engine.engine import ReportingEngine

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="QR-AI: Qualitative Research AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logger = setup_logging(args.debug)

    try:
        current_dir = os.getcwd()
        project_data_dir = os.path.join(current_dir, 'project_data')
        os.makedirs(project_data_dir, exist_ok=True)
        data_file_path = os.path.join(project_data_dir, 'qr-ai-data.json')
        
        logger.info(f"Initializing QR-AI with data file: {data_file_path}")
        
        plm = ProjectLifecycleManager(data_file_path)
        ppe = PreprocessorEngine()
        ae = AnalysisEngine()
        re = ReportingEngine()

        logger.info("Checking for existing project")
        project_name = plm.get_project(current_dir)

        if not project_name:
            logger.info("No existing project found. Prompting to create a new one.")
            create_project = input("Do you want to create a new project? (Y/n): ").lower()
            if create_project != 'n':
                project_name = plm.create_project(current_dir)

        if project_name:
            logger.info(f"Project: {project_name}")
            project_config = plm.data_manager.get_project_config(project_name)
            project_pi = plm.get_project_pi(project_name)
            
            logger.info(f"Principal Investigator: {project_pi}")
            
            print(f"Welcome to QR-AI Interactive CLI!")
            print(f"Current project: {project_name}")
            print(f"Principal Investigator: {project_pi}")
            
            logger.info("Starting interactive CLI")
            interactive_cli(plm, ppe, ae, re, project_name, project_config)
        else:
            logger.warning("No project selected or created. Exiting QR-AI.")
            print("Exiting QR-AI. No project selected or created.")

    except KeyboardInterrupt:
        print("\nQR-AI interrupted. Exiting gracefully.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        else:
            print("Run with --debug flag for more detailed error information.")
        sys.exit(1)

if __name__ == "__main__":
    main()
