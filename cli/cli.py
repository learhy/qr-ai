import click

@click.group()
def cli():
    """QR-AI - Customer Interview Analysis Tool"""
    pass

@cli.command()
def start():
    """Start the QR-AI CLI tool"""
    click.echo("QR-AI CLI tool started")

def interactive_cli(admin_service, plm, ppe, ae, re):
    click.echo("Welcome to QR-AI Interactive CLI!")
    while True:
        command = click.prompt("Enter a command (or 'exit' to quit)")
        if command.lower() == 'exit':
            break
        elif command.lower() == 'help':
            click.echo("Available commands: create_user, create_project, analyze, report")
        elif command.lower() == 'create_user':
            username = click.prompt("Enter username")
            admin_service.create_user(username)
        elif command.lower() == 'create_project':
            project_name = click.prompt("Enter project name")
            plm.create_project(project_name)
        elif command.lower() == 'analyze':
            text = click.prompt("Enter text to analyze")
            result = ae.submit_for_analysis(text)
            click.echo(f"Analysis result: {result}")
        elif command.lower() == 'report':
            project_name = click.prompt("Enter project name")
            report = re.generate_webpage(project_name)
            click.echo(f"Generated report: {report}")
        else:
            click.echo("Unknown command. Type 'help' for available commands.")

if __name__ == '__main__':
    cli()
