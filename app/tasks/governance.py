from app.database import SessionLocal
from app.services.governance.engine import compute_quality_report, execute_governance_pipeline
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_governance_pipeline")
def run_governance_pipeline_task(self):
    self.update_state(state="PROGRESS", meta={"stage": "starting"})
    db = SessionLocal()
    try:
        results = execute_governance_pipeline(db)
        return {"status": "completed", "phases": results}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True, name="generate_quality_report")
def generate_quality_report_task(self):
    db = SessionLocal()
    try:
        report = compute_quality_report(db)
        return {"status": "completed", **report}
    finally:
        db.close()
