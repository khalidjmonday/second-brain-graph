export default function BrandMark({ size = 18 }) {
  return <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <path d="M20 3.8 33.8 11.7v16.6L20 36.2 6.2 28.3V11.7L20 3.8Z" stroke="currentColor" strokeOpacity=".55" strokeWidth="1.25" />
    <path d="m11.5 21 8.3-9.5 8.7 7.6-10 9.2-7-7.3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="m19.8 11.5.3 16.8m-8.6-7.3 17-1.9" stroke="currentColor" strokeOpacity=".65" strokeWidth="1" strokeLinecap="round" />
    <g fill="#d8e7fa" stroke="#111a29" strokeWidth="1.6"><circle cx="11.5" cy="21" r="2.7"/><circle cx="19.8" cy="11.5" r="2.7"/><circle cx="28.5" cy="19.1" r="2.7"/><circle cx="18.5" cy="28.3" r="2.7"/></g>
  </svg>;
}
