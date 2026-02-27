
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import json

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.search.query_router import universal_search, QueryIntent
from core.search.vector_search import search_by_vector
from core.search.hybrid_search import hybrid_search

class TestTypeSpecificSearch(unittest.TestCase):

    def setUp(self):
        self.mock_results_vec = [
            {
                'chunk_id': 1,
                'doc_id': 101,
                'source_type': 'step',
                'source_title': 'Oven SOP Step 1',
                'content': '1. Turn on the Oven power.',
                'similarity': 0.9,
                'document': {'filename': 'Oven_SOP_N706.pdf', 'doc_type': 'Procedure'}
            },
            {
                'chunk_id': 2,
                'doc_id': 102,
                'source_type': 'section',
                'source_title': 'General Safety',
                'content': 'Safety first.',
                'similarity': 0.8,
                'document': {'filename': 'General_Safety.pdf', 'doc_type': 'Manual'}
            }
        ]
        
        self.mock_results_kw = [
             {
                'id': 101,
                'file_name': 'Oven_SOP_N706.pdf',
                'file_type': 'Procedure',
                'preview': '1. Turn on the Oven power.'
            }
        ]

    @patch('core.search.query_router._execute_search')
    @patch('core.search.query_router._post_process_results')
    @patch('core.search.query_router._log_search_history')
    def test_universal_search_procedure_direct_retrieval(self, mock_log, mock_post, mock_exec):
        """Test Procedure Direct Retrieval logic in universal_search"""
        
        # Mock _execute_search to return high score Procedure doc
        # standardizing the result as post_process is bypassed
        mock_res = self.mock_results_vec[0].copy()
        mock_res['file_name'] = mock_res['document']['filename']
        
        mock_exec.return_value = [mock_res] # High score Oven SOP
        mock_post.side_effect = lambda results, q, i: results # Pass through
        
        # 1. Search with Procedure type and Station filter
        filters = {'station': 'Oven'}
        result = universal_search(
            query="Over start",
            query_type='procedure',
            filters=filters
        )
        
        # Check skip_llm is True (Direct Retrieval triggered)
        self.assertTrue(result['meta']['skip_llm'], "Should skip LLM for high confidence Procedure match")
        self.assertEqual(result['results'][0]['document']['filename'], 'Oven_SOP_N706.pdf')
        
    @patch('core.database.vector_ops.get_connection')
    @patch('core.ai_core.get_embedding')
    def test_vector_search_sql_filtering(self, mock_embed, mock_conn):
        """Test SQL generation in vector_search (via mock cursor)"""
        
        # Mock embedding
        mock_embed.return_value = ([0.1]*1536, {})
        
        # Mock DB Cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [] # No results needed, just checking SQL
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        # Call search_by_vector with filters
        filters = {'doc_type': 'Troubleshooting', 'product': 'N706'}
        from core.search.vector_search import search_by_vector
        search_by_vector("issue", filters=filters)
        
        # Check SQL query in execute call
        call_args = mock_cursor.execute.call_args
        if call_args:
            sql = call_args[0][0]
            params = call_args[0][1]
            
            print(f"Generated SQL: {sql}")
            print(f"Params: {params}")
            
            self.assertIn("JOIN documents d", sql)
            self.assertIn("d.doc_type = ?", sql)
            self.assertIn("d.filename LIKE ?", sql)
            self.assertIn("Troubleshooting", params)
            self.assertTrue(any("N706" in str(p) for p in params))

    @patch('core.search.hybrid_search.search_by_vector')
    @patch('core.search.hybrid_search.search_documents_v2')
    @patch('core.database.get_chunks_by_doc_id')
    def test_hybrid_search_post_filtering(self, mock_get_chunks, mock_kw, mock_vec):
        """Test Hybrid Search post-filtering of keyword results"""
        
        # Mock Vector Search (Returns N706 doc)
        mock_vec.return_value = [self.mock_results_vec[0]]
        
        # Mock Keyword Search (Returns N706 and N500)
        mock_kw.return_value = [
            {'id': 101, 'file_name': 'Oven_SOP_N706.pdf', 'file_type': 'Procedure'},
            {'id': 202, 'file_name': 'Oven_SOP_N500.pdf', 'file_type': 'Procedure'} # Irrelevant product
        ]
        
        # Mock get_chunks (just return dummy)
        mock_get_chunks.return_value = [{'chunk_id': 99, 'source_title': 't', 'content': 'c'}]
        
        # Filter for N706
        filters = {'product': 'N706'}
        results = hybrid_search("Oven", filters=filters)
        
        # Result should NOT contain N500
        filenames = [r['document']['filename'] for r in results]
        self.assertIn('Oven_SOP_N706.pdf', filenames)
        self.assertNotIn('Oven_SOP_N500.pdf', filenames)

if __name__ == '__main__':
    unittest.main()
