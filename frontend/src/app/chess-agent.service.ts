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

export interface AgentSnapshot {
  moves: MoveResponse;
  evaluation: EvaluationResponse;
}

@Injectable({ providedIn: 'root' })
export class ChessAgentService {
  private readonly apiBase = '/api/v1';

  constructor(private readonly http: HttpClient) {}

  analyzePosition(fen: string): Observable<AgentSnapshot> {
    const encodedFen = encodeURIComponent(fen);
    return forkJoin({
      moves: this.http.get<MoveResponse>(`${this.apiBase}/moves/${encodedFen}`),
      evaluation: this.http.get<EvaluationResponse>(`${this.apiBase}/evaluate/${encodedFen}`)
    });
  }

  searchOpening(opening: string): Observable<VectorSearchResponse> {
    const params = new HttpParams().set('opening', opening);
    return this.http.get<VectorSearchResponse>(`${this.apiBase}/vector-search`, { params });
  }

  searchVideos(opening: string): Observable<VideoResponse> {
    return this.http.get<VideoResponse>(`${this.apiBase}/videos/${encodeURIComponent(opening)}`);
  }
}
