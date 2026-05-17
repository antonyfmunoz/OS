import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { CodeView } from './routes/CodeView'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/code" element={<CodeView />} />
        <Route path="*" element={<Navigate to="/code" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
