// src/components/upload/PdfDropzone.js (updated)
'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { supabase } from '@/lib/supabase';

export default function PdfDropzone() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [processedTransactions, setProcessedTransactions] = useState([]);

  const onDrop = useCallback((acceptedFiles) => {
    // Filter for only PDF files
    const pdfFiles = acceptedFiles.filter(
      file => file.type === 'application/pdf'
    );
    
    setFiles(pdfFiles);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024, // 10MB max size
  });

  const uploadFiles = async () => {
    if (files.length === 0) return;
    
    setUploading(true);
    setUploadStatus('Uploading...');
    setProcessedTransactions([]);
    
    try {
      // Get JWT token from Supabase session
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        throw new Error('You must be logged in to upload files');
      }
      
      const formData = new FormData();
      
      files.forEach((file) => {
        formData.append('files', file);
      });
      // console.log("Session token:", session.access_token);
      // console.log("Refresh token:", session.refresh_token);
      // Replace with your actual backend API endpoint
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        headers: {
          // Pass JWT token for authentication
          'Authorization': `Bearer ${session.access_token}`,
          'Refresh-token' : `${session.refresh_token}`
        },
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result = await response.json();
      setUploadStatus('Upload successful!');
      
      // Extract and display processed transactions
      const allTransactions = [];
      result.results.forEach(fileResult => {
        if (fileResult.result && fileResult.result.success) {
          allTransactions.push(...(fileResult.result.transactions || []));
        }
      });
      
      setProcessedTransactions(allTransactions);
      
      // Clear files after successful upload
      setFiles([]);
    } catch (error) {
      console.error('Error uploading files:', error);
      setUploadStatus(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div
        {...getRootProps()}
        className={`p-6 mt-4 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'}`}
      >
        <input {...getInputProps()} />
        
        {isDragActive ? (
          <p className="text-blue-500">Drop your PDF files here...</p>
        ) : (
          <div>
            <p className="mb-2">Drag & drop your credit card statements (PDF) here</p>
            <p className="text-sm text-gray-500">or click to select files</p>
          </div>
        )}
      </div>
      
      {files.length > 0 && (
        <div className="mt-4">
          <h3 className="font-medium">Selected Files:</h3>
          <ul className="mt-2 space-y-1">
            {files.map((file, index) => (
              <li key={index} className="text-sm">
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </li>
            ))}
          </ul>
          
          <button
            onClick={uploadFiles}
            disabled={uploading}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </button>
          
          {uploadStatus && (
            <p className={`mt-2 text-sm ${uploadStatus.includes('failed') ? 'text-red-500' : 'text-green-500'}`}>
              {uploadStatus}
            </p>
          )}
        </div>
      )}
      
      {processedTransactions.length > 0 && (
        <div className="mt-6">
          <h3 className="font-medium">Processed Transactions:</h3>
          <div className="mt-2 max-h-60 overflow-y-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Date</th>
                  <th className="px-4 py-2 text-left">Merchant</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {processedTransactions.map((tx, index) => (
                  <tr key={index} className="border-t">
                    <td className="px-4 py-2">{new Date(tx.date).toLocaleDateString()}</td>
                    <td className="px-4 py-2">{tx.merchant}</td>
                    <td className="px-4 py-2 text-right">
                      ${Math.abs(tx.charge).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}