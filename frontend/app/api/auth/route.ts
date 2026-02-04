import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function POST(request: NextRequest) {
  const { password } = await request.json()

  const correctPassword = process.env.BASIC_AUTH_PASSWORD

  if (!correctPassword) {
    // No password configured, allow access
    return NextResponse.json({ success: true })
  }

  if (password === correctPassword) {
    // Set auth cookie (httpOnly for security)
    const response = NextResponse.json({ success: true })
    response.cookies.set('violet_auth', 'authenticated', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    })
    return response
  }

  return NextResponse.json({ error: 'Invalid password' }, { status: 401 })
}

export async function DELETE() {
  // Logout - clear the cookie
  const response = NextResponse.json({ success: true })
  response.cookies.delete('violet_auth')
  return response
}
