import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { NgxChessBoardModule } from 'ngx-chess-board';
import { of, throwError } from 'rxjs';
import { AppComponent } from './app.component';
import { ChessAgentService } from './chess-agent.service';

describe('AppComponent', () => {
  let agent: jasmine.SpyObj<ChessAgentService>;

  beforeEach(async () => {
    agent = jasmine.createSpyObj<ChessAgentService>('ChessAgentService', [
      'analyzePosition',
      'coachPosition',
      'searchOpening',
      'searchVideos'
    ]);

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        importProvidersFrom(NgxChessBoardModule.forRoot()),
        { provide: ChessAgentService, useValue: agent }
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Agent ouvertures echecs');
  });

  it('analyzes the current board position', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    const fen = 'start fen';
    component.board = { getFEN: () => fen } as any;
    agent.analyzePosition.and.returnValue(of({
      moves: { fen, moves: [{ uci: 'e2e4', san: 'e4', white: 10, draws: 1, black: 9, games: 20 }] },
      evaluation: { fen, depth: 12, centipawns: 25, mate: null, best_move: 'e2e4' }
    }));

    component.analyzeCurrentPosition();

    expect(agent.analyzePosition).toHaveBeenCalledWith(fen);
    expect(component.loadingPosition).toBeFalse();
    expect(component.evaluation?.best_move).toBe('e2e4');
    expect(component.moveResponse?.moves.length).toBe(1);
  });

  it('stores position errors', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    component.board = { getFEN: () => 'bad fen' } as any;
    agent.analyzePosition.and.returnValue(throwError(() => ({ error: { detail: 'Invalid FEN syntax' } })));

    component.analyzeCurrentPosition();

    expect(component.loadingPosition).toBeFalse();
    expect(component.positionError).toBe('Invalid FEN syntax');
  });

  it('loads context and videos for an opening', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    component.openingQuery = 'sicilienne';
    agent.searchOpening.and.returnValue(of({
      query: 'sicilienne',
      results: [{ opening: 'Defense sicilienne', eco: 'B20', text: '1.e4 c5', source: 'test', score: 0.9 }]
    }));
    agent.searchVideos.and.returnValue(of({
      opening: 'sicilienne',
      videos: [{
        video_id: 'abc',
        title: 'Sicilienne',
        description: 'Opening',
        channel: 'Coach',
        published_at: '2026-01-01',
        url: 'https://youtu.be/abc',
        embed_url: 'https://youtube.com/embed/abc',
        thumbnail_url: null
      }],
      count: 1
    }));

    component.loadResources();

    expect(component.loadingResources).toBeFalse();
    expect(component.contextResults.length).toBe(1);
    expect(component.videos.length).toBe(1);
  });

  it('asks the coach for a unified recommendation', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    const fen = 'coach fen';
    component.board = { getFEN: () => fen } as any;
    component.openingQuery = 'Defense sicilienne';
    agent.coachPosition.and.returnValue(of({
      fen,
      opening: 'Defense sicilienne',
      selected_tools: ['stockfish', 'lichess', 'milvus', 'youtube'],
      legal_moves: ['g1f3'],
      evaluation: { fen, depth: 12, centipawns: 20, mate: null, best_move: 'g1f3' },
      theory_moves: [{ uci: 'g1f3', san: 'Nf3', white: 12, draws: 2, black: 8, games: 22 }],
      context: [{ opening: 'Defense sicilienne', eco: 'B20', text: 'Developper les pieces.', source: 'test', score: 0.9 }],
      videos: [{
        video_id: 'abc',
        title: 'Sicilienne',
        description: 'Opening',
        channel: 'Coach',
        published_at: '2026-01-01',
        url: 'https://youtu.be/abc',
        embed_url: 'https://youtube.com/embed/abc',
        thumbnail_url: null
      }],
      warnings: ['YouTube indisponible'],
      recommendation: 'Jouer Nf3 et developper.'
    }));

    component.askCoach();

    expect(agent.coachPosition).toHaveBeenCalledWith(fen, 'Defense sicilienne');
    expect(component.loadingCoach).toBeFalse();
    expect(component.coachResponse?.recommendation).toContain('Nf3');
    expect(component.evaluation?.best_move).toBe('g1f3');
    expect(component.contextResults.length).toBe(1);
    expect(component.videos.length).toBe(1);
  });

  it('stores coach errors', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    component.board = { getFEN: () => 'bad fen' } as any;
    agent.coachPosition.and.returnValue(throwError(() => ({ error: { detail: 'Invalid FEN syntax' } })));

    component.askCoach();

    expect(component.loadingCoach).toBeFalse();
    expect(component.coachError).toBe('Invalid FEN syntax');
  });

  it('keeps coach advice when the evaluation is unavailable', () => {
    const component = TestBed.createComponent(AppComponent).componentInstance;
    component.board = { getFEN: () => 'coach fen' } as any;
    agent.coachPosition.and.returnValue(of({
      fen: 'normalized fen', opening: '', selected_tools: [], legal_moves: [],
      evaluation: null, theory_moves: [], context: [], videos: [],
      warnings: ['Stockfish indisponible'], recommendation: 'Developper les pieces.'
    }));

    component.askCoach();

    expect(component.currentFen).toBe('normalized fen');
    expect(component.coachResponse?.recommendation).toBe('Developper les pieces.');
    expect(component.loadingCoach).toBeFalse();
  });

  it('uses fallback messages for network errors and preserves the first resource error', () => {
    const component = TestBed.createComponent(AppComponent).componentInstance;
    component.board = { getFEN: () => 'fen' } as any;
    agent.analyzePosition.and.returnValue(throwError(() => new Error('Network error')));
    agent.coachPosition.and.returnValue(throwError(() => new Error('Network error')));
    agent.searchOpening.and.returnValue(throwError(() => new Error('Network error')));
    agent.searchVideos.and.returnValue(throwError(() => ({ error: { detail: 'YouTube unavailable' } })));

    component.analyzeCurrentPosition();
    component.askCoach();
    component.loadResources();

    expect(component.positionError).toBe('Analyse indisponible');
    expect(component.coachError).toBe('Conseil agent indisponible');
    expect(component.resourceError).toBe('Contexte indisponible');
    expect(component.loadingPosition).toBeFalse();
    expect(component.loadingCoach).toBeFalse();
    expect(component.loadingResources).toBeFalse();
  });

  it('keeps loading videos if context search fails', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    agent.searchOpening.and.returnValue(throwError(() => ({ error: { detail: 'Milvus unavailable' } })));
    agent.searchVideos.and.returnValue(of({ opening: 'Defense sicilienne', videos: [], count: 0 }));

    component.loadResources();

    expect(component.resourceError).toBe('Milvus unavailable');
    expect(agent.searchVideos).toHaveBeenCalled();
    expect(component.loadingResources).toBeFalse();
  });

  it('stores video errors when video search fails', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    agent.searchOpening.and.returnValue(of({ query: 'Defense sicilienne', results: [] }));
    agent.searchVideos.and.returnValue(throwError(() => ({ error: { detail: 'YouTube key missing' } })));

    component.loadResources();

    expect(component.videos).toEqual([]);
    expect(component.resourceError).toBe('YouTube key missing');
    expect(component.loadingResources).toBeFalse();
  });

  it('skips empty position and opening requests', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    component.board = { getFEN: () => '' } as any;
    component.openingQuery = '   ';

    component.analyzeCurrentPosition();
    component.askCoach();
    component.loadResources();

    expect(agent.analyzePosition).not.toHaveBeenCalled();
    expect(agent.coachPosition).not.toHaveBeenCalled();
    expect(agent.searchOpening).not.toHaveBeenCalled();
  });

  it('handles board utility actions and trackers', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    const board = jasmine.createSpyObj('board', ['reverse', 'getFEN']);
    component.board = board;

    component.reverseBoard();
    component.onMoveChange();

    expect(board.reverse).toHaveBeenCalled();
    expect(agent.analyzePosition).not.toHaveBeenCalled();
    expect(component.trackMove(0, { uci: 'e2e4', white: 1, draws: 0, black: 0, games: 1 })).toBe('e2e4');
    expect(component.trackContext(0, { opening: 'Defense', eco: 'B20', text: '', source: '', score: 1 })).toBe('Defense-B20');
    expect(component.trackTool(0, 'stockfish')).toBe('stockfish');
    expect(component.trackWarning(0)).toBe(0);
    expect(component.trackVideo(0, {
      video_id: 'abc',
      title: '',
      description: '',
      channel: '',
      published_at: '',
      url: '',
      embed_url: '',
      thumbnail_url: null
    })).toBe('abc');
  });

  it('resets board state', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    const board = jasmine.createSpyObj('board', ['reset', 'getFEN']);
    board.getFEN.and.returnValue('reset fen');
    component.board = board;
    component.positionError = 'old';
    component.coachError = 'old coach';
    component.coachResponse = {
      fen: 'old',
      opening: '',
      selected_tools: [],
      legal_moves: [],
      evaluation: null,
      theory_moves: [],
      context: [],
      videos: [],
      warnings: [],
      recommendation: 'old'
    };
    component.evaluation = { fen: 'old', depth: 1, centipawns: 0, mate: null, best_move: null };

    component.resetBoard();

    expect(board.reset).toHaveBeenCalled();
    expect(component.currentFen).toBe('reset fen');
    expect(component.evaluation).toBeUndefined();
    expect(component.positionError).toBe('');
    expect(component.coachError).toBe('');
    expect(component.coachResponse).toBeUndefined();
  });
});
