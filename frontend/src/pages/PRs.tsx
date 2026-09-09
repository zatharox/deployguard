import { Link } from 'react-router-dom';

export default function PRs() {
  return (
    <div>
      <h1>Pull Requests</h1>

      <p>
        View analyzed pull requests and their deployment risk.
      </p>

      <Link to="/prs/999">
        Open PR #999
      </Link>
    </div>
  );
}