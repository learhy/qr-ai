import click
import webbrowser
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from reporting_engine.engine import ReportingEngine

def interactive_cli(plm, ppe, ae, project_name, project_config):
    re = ReportingEngine()
    click.echo(f"Welcome to QR-AI Interactive CLI! Current project: {project_name}")
    
    commands = ['set_learning_goal', 'show_learning_goals', 'import', 'set_interview', 'associate_file', 'status', 'analyze', 'report', 'help', 'exit']
    command_completer = WordCompleter(commands, ignore_case=True)
    session = PromptSession(completer=command_completer)

    while True:
        try:
            command = session.prompt(f"{project_name}> ").strip().lower()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if command == 'exit':
            break
        elif command == 'help':
            click.echo("Available commands: " + ", ".join(commands))
        elif command == 'set_learning_goal':
            print("Enter learning goal (Markdown supported). Press Ctrl+D (Unix) or Ctrl+Z (Windows) followed by Enter to finish:")
            goal_lines = []
            while True:
                try:
                    line = input()
                    goal_lines.append(line)
                except EOFError:
                    break
            goal = "\n".join(goal_lines)
            plm.set_learning_goal(project_name, goal)
        elif command == 'import':
            plm.import_files(project_name)
        elif command == 'set_interview':
            interviewee = session.prompt("Enter interviewee name: ")
            interviewer = session.prompt("Enter interviewer name: ")
            date = session.prompt("Enter interview date (YYYY-MM-DD): ")
            interview_name = session.prompt("Enter interview name: ")
            description = session.prompt("Enter interview description (optional): ")
            plm.set_interview(project_name, interview_name, interviewee, interviewer, date, description)
        elif command == 'associate_file':
            filename = session.prompt("Enter filename to associate: ")
            interview_name = session.prompt("Enter interview name: ")
            plm.associate_file_with_interview(project_name, filename, interview_name)
        elif command == 'status':
            plm.status(project_name)
        elif command == 'table_status':
            plm.table_status(project_name)
        elif command.startswith('analyze'):
            parts = command.split()
            if len(parts) > 1:
                argument = parts[1]
            else:
                argument = 'all'
            
            learning_goals = plm.get_learning_goals(project_name)
            if not learning_goals:
                click.echo("Learning goals have not been set.")
                if click.confirm("Would you like to set learning goals now?"):
                    print("Enter learning goal (Markdown supported). Press Ctrl+D (Unix) or Ctrl+Z (Windows) followed by Enter to finish:")
                    goal_lines = []
                    while True:
                        try:
                            line = input()
                            goal_lines.append(line)
                        except EOFError:
                            break
                    goal = "\n".join(goal_lines)
                    plm.set_learning_goal(project_name, goal)
                else:
                    continue
            
            ae.analyze_interviews(project_name, argument)
        elif command == 'report':
            try:
                output_file = re.generate_webpage(project_name)
                click.echo(f"Generated report: {output_file}")
                webbrowser.open('file://' + os.path.abspath(output_file))
                click.echo("The report has been opened in your default web browser.")
            except Exception as e:
                click.echo(f"An error occurred while generating the report: {str(e)}")
        elif command == 'show_learning_goals':
            plm.show_preprocessed_learning_goals(project_name)
        else:
            click.echo("Unknown command. Type 'help' for available commands.")

if __name__ == '__main__':
    pass  # This file should not be run directly
