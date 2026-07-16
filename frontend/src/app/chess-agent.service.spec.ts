import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ChessAgentService } from './chess-agent.service';

describe('ChessAgentService', () => {
  let service: ChessAgentService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ChessAgentService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('loads moves and evaluation for a FEN', () => {
    const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    let result: unknown;

    service.analyzePosition(fen).subscribe((response) => (result = response));

    const movesRequest = http.expectOne((req) => req.url === '/api/v1/moves');
    expect(movesRequest.request.params.get('fen')).toBe(fen);
    movesRequest.flush({ fen, moves: [] });

    const evaluationRequest = http.expectOne((req) => req.url === '/api/v1/evaluate');
    expect(evaluationRequest.request.params.get('fen')).toBe(fen);
    evaluationRequest.flush({
      fen,
      depth: 12,
      centipawns: 20,
      mate: null,
      best_move: 'e2e4'
    });

    expect(result).toEqual({
      moves: { fen, moves: [] },
      evaluation: { fen, depth: 12, centipawns: 20, mate: null, best_move: 'e2e4' }
    });
  });

  it('searches opening context', () => {
    service.searchOpening('sicilienne').subscribe();

    const request = http.expectOne((req) => req.url === '/api/v1/vector-search');
    expect(request.request.params.get('opening')).toBe('sicilienne');
    request.flush({ query: 'sicilienne', results: [] });
  });

  it('searches videos for an opening', () => {
    service.searchVideos('Defense sicilienne').subscribe();

    const request = http.expectOne((req) => req.url === '/api/v1/videos');
    expect(request.request.params.get('opening')).toBe('Defense sicilienne');
    request.flush({
      opening: 'Defense sicilienne',
      videos: [],
      count: 0
    });
  });
});
