import './App.css';

const productSteps = [
  {
    description:
      'Defina cargos, competências, localização e o que você prefere evitar.',
    number: '01',
    title: 'Dê contexto ao seu perfil',
  },
  {
    description:
      'Reúna vagas encontradas na web e compare cada uma com os seus critérios.',
    number: '02',
    title: 'Revise o que importa',
  },
  {
    description:
      'Registre candidaturas, entrevistas, ofertas e os próximos passos.',
    number: '03',
    title: 'Acompanhe o processo',
  },
];

function App() {
  return (
    <main className="paper-app">
      <header className="site-header" role="banner">
        <div className="header-inner">
          <a className="brand" href="#inicio" aria-label="Job Finder, início">
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-name">Job Finder</span>
          </a>

          <nav aria-label="Navegação principal">
            <a href="#como-funciona">Como funciona</a>
            <a href="#fluxo">Fluxo</a>
            <a href="#perfil">Perfil</a>
          </nav>

          <div className="header-meta">
            <span className="meta-label">LOCAL · PRIVADO</span>
            <button className="header-action" type="button">
              Abrir perfil
            </button>
          </div>
        </div>
      </header>

      <section
        className="editorial-hero"
        id="inicio"
        aria-labelledby="page-title"
      >
        <div className="hero-copy">
          <p className="eyebrow">PLATAFORMA LOCAL DE VAGAS</p>
          <h1
            id="page-title"
            aria-label="Encontre oportunidades. Prepare-se para avançar."
          >
            Encontre oportunidades.
            <br />
            <em>Prepare-se para avançar.</em>
          </h1>
          <p className="lede">
            Um espaço simples para transformar sua busca de emprego em um
            processo que você consegue acompanhar.
          </p>
          <div className="hero-actions">
            <button className="primary-button" type="button">
              Configurar meu perfil
            </button>
            <a className="text-button" href="#como-funciona">
              Ver como funciona <span aria-hidden="true">↗</span>
            </a>
          </div>
          <p className="privacy-note">
            <span className="status-dot" aria-hidden="true" />
            Dados ficam neste computador.
          </p>
        </div>

        <aside
          className="workspace-card"
          id="perfil"
          aria-labelledby="workspace-title"
        >
          <div className="card-topline">
            <span className="meta-label">01 · SEU ESPAÇO DE BUSCA</span>
            <span className="card-status">PRONTO</span>
          </div>
          <div className="card-body">
            <p className="card-kicker">PRIMEIRO PASSO</p>
            <h2 id="workspace-title">Seu perfil ainda não foi configurado.</h2>
            <p>
              Comece dizendo que tipo de oportunidade faz sentido para você. O
              restante do espaço se adapta a essas escolhas.
            </p>
            <div className="progress-line" aria-label="Etapa 1 de 3">
              <span className="progress-fill" />
            </div>
            <div className="progress-caption">
              <span>Perfil</span>
              <span>1 de 3 etapas</span>
            </div>
          </div>
          <div className="card-footer">
            <span className="mono-note">SEM CONTA · SEM NUVEM</span>
            <span className="arrow-icon" aria-hidden="true">
              →
            </span>
          </div>
        </aside>
      </section>

      <section
        className="process-section"
        id="como-funciona"
        aria-labelledby="process-title"
      >
        <div className="section-heading">
          <p className="eyebrow">COMO FUNCIONA</p>
          <h2 id="process-title">
            Uma busca mais clara, do primeiro anúncio à próxima conversa.
          </h2>
        </div>

        <ol className="step-list" id="fluxo">
          {productSteps.map((step) => (
            <li className="step-row" key={step.number}>
              <span className="step-number">{step.number}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
              <span className="step-arrow" aria-hidden="true">
                ↗
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="closing-cta" aria-labelledby="closing-title">
        <div>
          <p className="eyebrow">PRÓXIMA ETAPA</p>
          <h2 id="closing-title">
            Sua próxima oportunidade começa com contexto.
          </h2>
        </div>
        <button className="inverse-button" type="button">
          Começar agora <span aria-hidden="true">↗</span>
        </button>
      </section>

      <footer className="site-footer">
        <span>JOB FINDER · LOCAL</span>
        <span>v0.1 · DADOS LOCAIS</span>
      </footer>
    </main>
  );
}

export default App;
