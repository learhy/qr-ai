import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

def interactive_cli(plm, ppe, ae, re, project_name, project_config):
    click.echo(f"Welcome to QR-AI Interactive CLI! Current project: {project_name}")
    
    commands = ['set_learning_goal', 'import', 'set_interview', 'associate_file', 'status', 'analyze', 'report', 'help', 'exit']
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
            goal = session.prompt("Enter learning goal: ")
            plm.set_learning_goal(project_name, goal)
        elif command == 'import':
            plm.import_files(project_name)
        elif command == 'set_interview':
            interviewee = session.prompt("Enter interviewee name: ")
            interviewer = session.prompt("Enter interviewer name: ")
            date = session.prompt("Enter interview date (YYYY-MM-DD): ")
            plm.set_interview(project_name, interviewee, interviewer, date)
        elif command == 'associate_file':
            filename = session.prompt("Enter filename to associate: ")
            interview_name = session.prompt("Enter interview name: ")
            plm.associate_file_with_interview(project_name, filename, interview_name)
        elif command == 'status':
            plm.status(project_name)
        elif command == 'analyze':
            text = session.prompt("Enter text to analyze: ")
            result = ae.submit_for_analysis(text)
            click.echo(f"Analysis result: {result}")
        elif command == 'report':
            report = re.generate_webpage(project_name)
            click.echo(f"Generated report: {report}")
        else:
            click.echo("Unknown command. Type 'help' for available commands.")

if __name__ == '__main__':
    pass  # This file should not be run directly
