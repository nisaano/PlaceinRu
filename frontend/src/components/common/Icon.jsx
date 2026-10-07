const paths = {
  pin: (
    <>
      <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  home: (
    <>
      <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" />
    </>
  ),
  chat: (
    <>
      <path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 9 9 0 0 1-4-.9L4 20l1.2-3.1A7.2 7.2 0 0 1 4 12c0-4.4 3.6-8 8-8s8 3.1 8 7.5Z" />
      <path d="M8 12h.01M12 12h.01M16 12h.01" />
    </>
  ),
  trip: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M7 3v4M17 3v4M3 10h18M8 14h3M8 17h7" />
    </>
  ),
  heart: (
    <path d="M20.8 8.8c0 5.2-8.8 11-8.8 11S3.2 14 3.2 8.8A4.8 4.8 0 0 1 12 6.1a4.8 4.8 0 0 1 8.8 2.7Z" />
  ),
  ticket: (
    <>
      <path d="M4 7a2 2 0 0 0 0 4v4a2 2 0 0 0 0 4h16a2 2 0 0 0 0-4v-4a2 2 0 0 0 0-4Z" />
      <path d="M13 7v2m0 3v2m0 3v2" />
    </>
  ),
  bed: (
    <>
      <path d="M3 18v-8a2 2 0 0 1 2-2h5a3 3 0 0 1 3 3v7M3 15h18v3M17 8h2a2 2 0 0 1 2 2v5" />
      <circle cx="7" cy="11" r="1.5" />
    </>
  ),
  landmark: (
    <>
      <path d="m3 9 9-6 9 6M5 10h14M6 10v8m4-8v8m4-8v8m4-8v8M3 21h18M4 18h16" />
    </>
  ),
  food: (
    <>
      <path d="M4 3v7a3 3 0 0 0 6 0V3M7 3v18M17 3v18m0-18c-2 2-3 4-3 7h6c0-3-1-5-3-7Z" />
    </>
  ),
  guide: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0M18 4l3 3-3 3" />
    </>
  ),
  file: (
    <>
      <path d="M6 3h8l5 5v13H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
      <path d="M14 3v6h5M8 13h8M8 17h6" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  arrow: (
    <>
      <path d="M4 12h15M13 5l7 7-7 7" />
    </>
  ),
  send: (
    <>
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  menu: (
    <>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </>
  ),
  close: (
    <>
      <path d="m6 6 12 12M18 6 6 18" />
    </>
  ),
  chevron: <path d="m6 9 6 6 6-6" />,
  check: <path d="m5 12 4 4L19 6" />,
  plus: (
    <>
      <path d="M12 5v14M5 12h14" />
    </>
  ),
  alert: (
    <>
      <path d="M10.3 3.9 2.5 17.4A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 1.7-2.6L13.7 3.9a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9v4m0 3h.01" />
    </>
  ),
  edit: (
    <>
      <path d="m4 16-.8 4.8L8 20l11.5-11.5a2.1 2.1 0 0 0-3-3Z" />
      <path d="m14.5 6.5 3 3" />
    </>
  ),
}

export function Icon({ name, size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.pin}
    </svg>
  )
}
