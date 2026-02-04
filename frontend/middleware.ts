import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Basic Auth middleware for password protection
export function middleware(request: NextRequest) {
  const basicAuthUser = process.env.BASIC_AUTH_USERNAME
  const basicAuthPassword = process.env.BASIC_AUTH_PASSWORD

  // Skip auth if not configured
  if (!basicAuthUser || !basicAuthPassword) {
    return NextResponse.next()
  }

  // Check for Authorization header
  const authHeader = request.headers.get('authorization')

  if (!authHeader || !authHeader.startsWith('Basic ')) {
    return new NextResponse('Authentication required', {
      status: 401,
      headers: {
        'WWW-Authenticate': 'Basic realm="SuperTruth Violet"',
      },
    })
  }

  // Decode and verify credentials
  try {
    const base64Credentials = authHeader.split(' ')[1]
    const credentials = atob(base64Credentials)
    const [username, password] = credentials.split(':')

    if (username === basicAuthUser && password === basicAuthPassword) {
      return NextResponse.next()
    }
  } catch {
    // Invalid auth header format
  }

  return new NextResponse('Invalid credentials', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="SuperTruth Violet"',
    },
  })
}

// Apply to all routes except static files
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
