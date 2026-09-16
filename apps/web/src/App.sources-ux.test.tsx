import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
afterEach(() => vi.unstubAllGlobals());
function setup({
  configured = true,
  locked = false,
  environment = false,
  fail = false,
  testFailure = false,
} = {}) {
  let exists = configured;
  const request = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (fail && url === '/api/search/providers')
      return new Response('{}', { status: 500 });
    const status = {
      provider: 'jsearch',
      configured: exists,
      unlocked: exists && !locked,
      storage: exists
        ? environment
          ? 'environment'
          : 'encrypted_database'
        : 'not_configured',
    };
    let data: unknown = null;
    if (url === '/api/vault') data = { configured: true, unlocked: !locked };
    if (url === '/api/search/providers') data = [status];
    if (url === '/api/search/providers/jsearch' && init?.method === 'DELETE') {
      exists = false;
      data = {
        ...status,
        configured: false,
        unlocked: false,
        storage: 'not_configured',
      };
    }
    if (url === '/api/search/providers/jsearch/test' && testFailure)
      return new Response(
        JSON.stringify({
          detail: 'Limite da fonte atingido. Aguarde a renovação da cota.',
        }),
        { status: 429 },
      );
    if (url === '/api/search/providers/jsearch/test')
      data = {
        provider: 'jsearch',
        status: 'connected',
        message: 'A fonte respondeu ao teste. Nenhuma vaga foi salva.',
      };
    if (
      String(url).startsWith('/api/search/providers/') &&
      init?.method === 'PUT'
    ) {
      exists = true;
      data = {
        ...status,
        provider: String(url).split('/').at(-1),
        configured: true,
        unlocked: true,
        storage: 'encrypted_database',
      };
    }
    if (url === '/api/sources') data = [];
    if (url === '/api/jobs') data = { items: [] };
    return new Response(JSON.stringify(data));
  });
  vi.stubGlobal('fetch', request);
  window.history.replaceState({}, '', '/configuracoes/fontes');
  render(<App />);
  return request;
}
describe('JF-819 fontes e configurações', () => {
  it('cadastra Adzuna com dois campos e limpa o rascunho ao trocar integração', async () => {
    const request = setup({ configured: false });
    const jsearch = screen.getByRole('region', { name: 'JSearch' });
    const edit = within(jsearch).getByRole('button', {
      name: 'Cadastrar credencial',
    });
    await waitFor(() => expect(edit).toBeEnabled());
    fireEvent.click(edit);
    fireEvent.change(screen.getByLabelText('API key'), {
      target: { value: 'rascunho-do-jsearch' },
    });
    const adzunaEdit = within(
      screen.getByRole('region', { name: 'Adzuna' }),
    ).getByRole('button', { name: 'Cadastrar credencial' });
    await waitFor(() => expect(adzunaEdit).toBeEnabled());
    fireEvent.click(adzunaEdit);
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Adzuna app ID'), {
      target: { value: 'id-teste' },
    });
    fireEvent.change(screen.getByLabelText('Adzuna app key'), {
      target: { value: 'chave-teste' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar credencial' }));
    await screen.findByText('Credencial criptografada no banco local.');
    const call = request.mock.calls.find(
      ([url, init]) =>
        url === '/api/search/providers/adzuna' && init?.method === 'PUT',
    );
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({
      app_id: 'id-teste',
      app_key: 'chave-teste',
    });
    expect(screen.getByLabelText('Adzuna app key')).toHaveValue('');
  });
  it('permite cancelar a confirmação sem testar ou remover a chave', async () => {
    const request = setup();
    const card = screen.getByRole('region', { name: 'JSearch' });
    fireEvent.click(
      await within(card).findByRole('button', { name: 'Remover credencial' }),
    );
    fireEvent.click(within(card).getByRole('button', { name: 'Cancelar' }));
    expect(
      request.mock.calls.some(([, init]) => init?.method === 'DELETE'),
    ).toBe(false);
    expect(
      within(card).queryByRole('button', {
        name: 'Confirmar remoção de JSearch',
      }),
    ).not.toBeInTheDocument();
  });
  it('mantém o erro de limite junto ao provider e permite nova ação', async () => {
    setup({ testFailure: true });
    const card = screen.getByRole('region', { name: 'JSearch' });
    fireEvent.click(
      await within(card).findByRole('button', { name: 'Testar conexão' }),
    );
    fireEvent.click(
      within(card).getByRole('button', { name: 'Confirmar teste de JSearch' }),
    );
    expect(await within(card).findByRole('alert')).toHaveTextContent(
      'Limite da fonte atingido',
    );
    expect(
      within(card).getByRole('button', { name: 'Testar conexão' }),
    ).toBeEnabled();
  });
  it('separa cada integração das fontes públicas e não mostra senha nem editor por padrão', async () => {
    setup();
    const card = await screen.findByRole('region', { name: 'JSearch' });
    expect(await within(card).findByText('Disponível')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Fontes públicas' }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Senha do cofre')).not.toBeInTheDocument();
    fireEvent.click(
      within(card).getByRole('button', { name: 'Atualizar credencial' }),
    );
    expect(screen.getByLabelText('API key')).toBeInTheDocument();
  });
  it('abre o cofre global pelo provider bloqueado', async () => {
    setup({ locked: true });
    const card = await screen.findByRole('region', { name: 'JSearch' });
    fireEvent.click(
      await within(card).findByRole('button', { name: 'Desbloquear cofre' }),
    );
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Senha do cofre')).toHaveLength(1);
  });
  it('só testa mediante confirmação de consumo de cota e não inicia uma busca agregada', async () => {
    const request = setup();
    const card = await screen.findByRole('region', { name: 'JSearch' });
    fireEvent.click(
      await within(card).findByRole('button', { name: 'Testar conexão' }),
    );
    expect(
      request.mock.calls.some(
        ([url]) => url === '/api/search/providers/jsearch/test',
      ),
    ).toBe(false);
    fireEvent.click(
      within(card).getByRole('button', { name: 'Confirmar teste de JSearch' }),
    );
    expect(
      await within(card).findByText(
        'A fonte respondeu ao teste. Nenhuma vaga foi salva.',
      ),
    ).toBeInTheDocument();
    expect(request.mock.calls.some(([url]) => url === '/api/search')).toBe(
      false,
    );
  });
  it('remove apenas a credencial escolhida depois de confirmação', async () => {
    const request = setup();
    const card = await screen.findByRole('region', { name: 'JSearch' });
    fireEvent.click(
      await within(card).findByRole('button', { name: 'Remover credencial' }),
    );
    expect(
      request.mock.calls.some(([, init]) => init?.method === 'DELETE'),
    ).toBe(false);
    fireEvent.click(
      within(card).getByRole('button', {
        name: 'Confirmar remoção de JSearch',
      }),
    );
    await waitFor(() =>
      expect(within(card).getByText('Não configurado')).toBeInTheDocument(),
    );
    expect(
      request.mock.calls
        .filter(([, init]) => init?.method === 'DELETE')
        .map(([url]) => url),
    ).toEqual(['/api/search/providers/jsearch']);
  });
  it('não oferece remoção de uma variável de ambiente', async () => {
    setup({ environment: true });
    const card = await screen.findByRole('region', { name: 'JSearch' });
    expect(
      await within(card).findByText('Configurada pelo ambiente'),
    ).toBeInTheDocument();
    expect(
      within(card).queryByRole('button', { name: 'Remover credencial' }),
    ).not.toBeInTheDocument();
  });
  it('mostra erro de leitura sem afirmar que a chave não existe', async () => {
    setup({ fail: true });
    const card = await screen.findByRole('region', { name: 'JSearch' });
    expect(
      await within(card).findByText('Estado indisponível'),
    ).toBeInTheDocument();
    expect(within(card).queryByText('Não configurado')).not.toBeInTheDocument();
  });
});
