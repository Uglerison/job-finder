import './App.css'

const onboardingSteps = [
  {
    description: 'Defina cargos, competências, localização e o que quer evitar.',
    number: '01',
    title: 'Configure seu perfil',
  },
  {
    description: 'Centralize vagas encontradas na web ou inclua um link manualmente.',
    number: '02',
    title: 'Revise oportunidades',
  },
  {
    description: 'Acompanhe candidaturas, entrevistas, ofertas e resultados.',
    number: '03',
    title: 'Movimente o pipeline',
  },
]

function App() {
  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <div className="hero-copy">
          <p className="eyebrow">JOB FINDER · LOCAL</p>
          <h1 id="page-title">Job Finder</h1>
          <p className="lede">Sua central local para encontrar e acompanhar vagas.</p>
          <p className="supporting-copy">
            Organize oportunidades, mantenha seu histórico de candidatura e acompanhe cada
            próxima etapa em um único lugar.
          </p>
          <div className="hero-actions">
            <button type="button">Configurar perfil</button>
            <button className="secondary-action" type="button">
              Conhecer o fluxo
            </button>
          </div>
        </div>

        <aside className="local-status" aria-label="Status do espaço de trabalho">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <p>Espaço de trabalho local</p>
            <strong>Pronto para configurar</strong>
          </div>
        </aside>
      </section>

      <section className="onboarding" aria-labelledby="onboarding-title">
        <div className="section-heading">
          <p className="eyebrow">PRIMEIROS PASSOS</p>
          <h2 id="onboarding-title">Construa uma busca que faça sentido para você.</h2>
        </div>

        <ol className="step-list">
          {onboardingSteps.map((step) => (
            <li className="step-card" key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  )
}

export default App
