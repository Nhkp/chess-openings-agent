import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { forkJoin, Observable } from 'rxjs';

export interface TheoryMove {
  uci: string;
  san?: string;
  white: number;
  draws: number;
  black: number;
  games: number;
}

export interface MoveResponse {
  fen: string;
  opening?: { eco?: string; name?: string };
  moves: TheoryMove[];
}

export interface EvaluationResponse {
  fen: string;
  depth: number;
  centipawns: number | null;
  mate: number | null;
  best_move: string | null;
}

export interface VectorSearchResult {
  opening: string;
  eco: string;
  text: string;
  source: string;
  score: number;
}

export interface VectorSearchResponse {
  query: string;
  results: VectorSearchResult[];
}

export interface VideoResult {
  video_id: string;
  title: string;
  description: string;
  channel: string;
  published_at: string;
  url: string;
  embed_url: string;
  thumbnail_url: string | null;
}

export interface VideoResponse {
  opening: string;
  videos: VideoResult[];
  count: number;
}

export interface CoachResponse {
  fen: string;
  opening: string;
  selected_tools: string[];
  legal_moves: string[];
  evaluation: EvaluationResponse | null;
  theory_moves: TheoryMove[];
  context: VectorSearchResult[];
  videos: VideoResult[];
  warnings: string[];
  recommendation: string;
}

export interface AgentSnapshot {
  moves: MoveResponse;
  evaluation: EvaluationResponse;
}

@Injectable({ providedIn: 'root' })
export class ChessAgentService {
  private readonly apiBase = '/api/v1';

  constructor(private readonly http: HttpClient) {}

  analyzePosition(fen: string): Observable<AgentSnapshot> {
    const params = new HttpParams().set('fen', fen);
    return forkJoin({
      moves: this.http.get<MoveResponse>(`${this.apiBase}/moves`, { params }),
      evaluation: this.http.get<EvaluationResponse>(`${this.apiBase}/evaluate`, { params })
    });
  }

  searchOpening(opening: string): Observable<VectorSearchResponse> {
    const params = new HttpParams().set('opening', opening);
    return this.http.get<VectorSearchResponse>(`${this.apiBase}/vector-search`, { params });
  }

  searchVideos(opening: string): Observable<VideoResponse> {
    const params = new HttpParams().set('opening', opening);
    return this.http.get<VideoResponse>(`${this.apiBase}/videos`, { params });
  }

  coachPosition(fen: string, opening: string): Observable<CoachResponse> {
    let params = new HttpParams().set('fen', fen);
    if (opening.trim()) {
      params = params.set('opening', opening.trim());
    }
    return this.http.get<CoachResponse>(`${this.apiBase}/coach`, { params });
  }
}
