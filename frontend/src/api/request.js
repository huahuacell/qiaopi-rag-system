import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 8000
})

request.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
)

export default request

