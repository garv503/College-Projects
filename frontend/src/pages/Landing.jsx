import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { useAuth } from '../auth';

const FEATURES = [
  {
    icon: 'bolt',
    title: 'Write without friction',
    body: 'A clean editor that gets out of the way. Type, save, done.',
  },
  {
    icon: 'pin',
    title: 'Pin what matters',
    body: 'Keep your most-used notes at the top of the list, always in reach.',
  },
  {
    icon: 'search',
    title: 'Find it instantly',
    body: 'Search across every title and body as your collection grows.',
  },
  {
    icon: 'lock',
    title: 'Yours alone',
    body: 'Every note is locked to its owner and visible only to you.',
  },
];

export default function Landing() {
  const { user } = useAuth();

  return (
    <main className="page" style={{ paddingTop: 0 }}>
      <section className="hero">
        <div className="container">
          <span className="eyebrow">
            <Icon name="bolt" /> Fast, private, yours
          </span>

          <h1>
            Every thought worth keeping, <span className="gradient-text">in one place</span>
          </h1>

          <p className="lead">
            Capture ideas, pin what matters, and find any note in seconds. E-Notes keeps your
            writing organised and to yourself.
          </p>

          <div className="hero-actions">
            {user ? (
              <>
                <Link className="btn btn-primary" to="/notes/new">
                  <Icon name="plus" /> Write a note
                </Link>
                <Link className="btn btn-outline" to="/notes">
                  <Icon name="notes" /> My notes
                </Link>
              </>
            ) : (
              <>
                <Link className="btn btn-primary" to="/register">
                  <Icon name="user-plus" /> Create free account
                </Link>
                <Link className="btn btn-outline" to="/login">
                  <Icon name="user" /> Sign in
                </Link>
              </>
            )}
          </div>

          <div className="feature-grid">
            {FEATURES.map((feature) => (
              <article className="feature" key={feature.title}>
                <div className="feature-icon">
                  <Icon name={feature.icon} />
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
