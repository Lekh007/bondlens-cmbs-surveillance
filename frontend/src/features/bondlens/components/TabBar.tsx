const TABS = [
  { label: 'Deal Summary', active: true },
  { label: 'Underwriting', active: false },
  { label: 'Loan Details', active: false },
  { label: 'Loan Vectors', active: false },
  { label: 'Cashflows', active: false },
  { label: 'Loan Events', active: false },
  { label: 'Market Color', active: false },
  { label: 'Documents', active: false },
];

export function TabBar() {
  return (
    <nav className="tabbar">
      {TABS.map(t => (
        <div key={t.label} className={`tab ${t.active ? 'active' : 'disabled'}`}>
          {t.label}
          {!t.active && <span className="soon">soon</span>}
        </div>
      ))}
    </nav>
  );
}
