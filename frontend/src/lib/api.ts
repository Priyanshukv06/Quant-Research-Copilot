import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL}/api/copilot`;

export interface QueryResponse {
  action: string;
  data: {
    intent?: any;
    screened_symbols?: any[];
    bq_query?: string;
    news?: any;
    synthesis?: any;
    report_markdown?: string;
    charts?: any[];
    error?: string;
  };
}

export async function submitQuery(query: string): Promise<QueryResponse> {
  try {
    const response = await axios.post(`${API_URL}/query`, { query });
    return response.data;
  } catch (error: any) {
    console.error("API Error:", error);
    return {
      action: "ERROR",
      data: {
        error: error.response?.data?.detail || error.message || "An unknown error occurred"
      }
    };
  }
}
