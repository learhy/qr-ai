from cli.cli import interactive_cli
from admin.admin import AdminService
from plm.plm import ProjectLifecycleManager
from ppe.ppe import PreprocessorEngine
from ae.ae import AnalysisEngine
from reporting_engine.engine import ReportingEngine

def main():
    admin_service = AdminService()
    plm = ProjectLifecycleManager()
    ppe = PreprocessorEngine()
    ae = AnalysisEngine()
    re = ReportingEngine()

    # Start the interactive CLI
    interactive_cli(admin_service, plm, ppe, ae, re)

if __name__ == "__main__":
    main()
