from sqlalchemy.orm import Session

from app.db.models import CodeNode, DependencyEdge, RepoFile, Repository
from app.services.graph_service import GraphService


def test_graph_service_module_aggregation_and_neighborhood(db_session: Session) -> None:
    repo = Repository(name="graph_demo", local_path="/tmp/graph_demo", status="ready")
    db_session.add(repo)
    db_session.flush()

    f1 = RepoFile(repo_id=repo.id, file_path="core.py", loc=20)
    f2 = RepoFile(repo_id=repo.id, file_path="api.py", loc=30)
    db_session.add_all([f1, f2])
    db_session.flush()

    m1 = CodeNode(repo_id=repo.id, file_id=f1.id, node_key="core", node_type="module", name="core", qualified_name="core", start_line=1, end_line=20)
    fn1 = CodeNode(repo_id=repo.id, file_id=f1.id, node_key="core.calc", node_type="function", name="calc", qualified_name="core.calc", start_line=1, end_line=5, fan_in=1)
    m2 = CodeNode(repo_id=repo.id, file_id=f2.id, node_key="api", node_type="module", name="api", qualified_name="api", start_line=1, end_line=30)
    fn2 = CodeNode(repo_id=repo.id, file_id=f2.id, node_key="api.route", node_type="function", name="route", qualified_name="api.route", start_line=5, end_line=10, fan_out=1)
    db_session.add_all([m1, fn1, m2, fn2])
    db_session.flush()

    db_session.add(DependencyEdge(repo_id=repo.id, source_node_id=fn2.id, target_node_id=fn1.id, edge_type="calls"))
    db_session.commit()

    gs = GraphService()
    mod_view = gs.get_graph_view(db_session, repo.id, level="module")
    assert mod_view["returned_nodes"] == 2
    assert mod_view["returned_edges"] == 1

    neigh = gs.get_node_neighborhood(db_session, repo.id, fn1.id)
    assert neigh is not None
    assert neigh["dependents"][0]["node_key"] == "api.route"
