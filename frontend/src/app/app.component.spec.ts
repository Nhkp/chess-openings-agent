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
    component.loadResources();

    expect(agent.analyzePosition).not.toHaveBeenCalled();
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
    component.evaluation = { fen: 'old', depth: 1, centipawns: 0, mate: null, best_move: null };

    component.resetBoard();

    expect(board.reset).toHaveBeenCalled();
    expect(component.currentFen).toBe('reset fen');
    expect(component.evaluation).toBeUndefined();
    expect(component.positionError).toBe('');
  });
});
