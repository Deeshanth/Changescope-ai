from sqlalchemy.orm import Session

from app.db.models import CodeNode, DependencyEdge, RepoFile, Repository


def test_create_repo_nodes_and_cascade_delete(db_session: Session) -> None:
    repo = Repository(name="demo", local_path="/tmp/demo", status="ready")
    db_session.add(repo)
    db_session.flush()

    repo_file = RepoFile(repo_id=repo.id, file_path="app.py", loc=10)
    db_session.add(repo_file)
    db_session.flush()

    fn_a = CodeNode(
        repo_id=repo.id,
        file_id=repo_file.id,
        node_key="app.caller",
        node_type="function",
        name="caller",
        qualified_name="app.caller",
        start_line=1,
        end_line=4,
    )
    fn_b = CodeNode(
        repo_id=repo.id,
        file_id=repo_file.id,
        node_key="app.callee",
        node_type="function",
        name="callee",
        qualified_name="app.callee",
        start_line=6,
        end_line=9,
    )
    db_session.add_all([fn_a, fn_b])
    db_session.flush()

    edge = DependencyEdge(
        repo_id=repo.id,
        source_node_id=fn_a.id,
        target_node_id=fn_b.id,
        edge_type="calls",
        line_number=2,
    )
    db_session.add(edge)
    db_session.commit()

    assert db_session.query(CodeNode).count() == 2
    assert db_session.query(DependencyEdge).count() == 1

    db_session.delete(repo)
    db_session.commit()

    assert db_session.query(RepoFile).count() == 0
    assert db_session.query(CodeNode).count() == 0
    assert db_session.query(DependencyEdge).count() == 0
