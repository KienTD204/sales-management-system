from pathlib import Path
from sqlalchemy import inspect, select
from app.extensions import db
from app.models import Product


def test_upgrade_real_week56_schema_preserves_seed_and_legacy_invoice(app):
    source=Path(__file__).parent/'fixtures/week56-database.sql'
    with app.app_context():
        db.session.remove();db.drop_all()
        sql='\n'.join(line for line in source.read_text(encoding='utf-8').splitlines() if not line.strip().startswith('--'))
        with db.engine.connect() as connection:
            for statement in sql.split(';'):
                if statement.strip():connection.exec_driver_sql(statement)
            connection.commit()
        assert len(inspect(db.engine).get_table_names())==14
    runner=app.test_cli_runner()
    first=runner.invoke(args=['upgrade-week678']);assert first.exit_code==0,first.output
    second=runner.invoke(args=['upgrade-week678']);assert second.exit_code==0,second.output
    with app.app_context():
        assert len(inspect(db.engine).get_table_names())==22
        assert db.session.get(Product,1).stock_quantity==18
        assert str(db.session.get(Product,1).price)=='25000.50'
    client=app.test_client();csrf=client.get('/api/csrf').json['data']['csrf_token']
    response=client.post('/api/login',json={'email':'owner.demo@example.com','password':'DemoOwner123!'},headers={'X-CSRF-Token':csrf})
    assert response.status_code==200
    invoices=client.get('/api/invoices').json['data'];assert len(invoices)==2
    assert client.get('/invoices/'+str(invoices[0]['invoice_id'])+'/print').status_code==200
