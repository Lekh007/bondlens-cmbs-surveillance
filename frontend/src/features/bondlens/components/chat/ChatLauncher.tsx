import { Sparkles } from 'lucide-react';

interface Props {
  onClick: () => void;
  hidden?: boolean;
}

export function ChatLauncher({ onClick, hidden }: Props) {
  if (hidden) return null;
  return (
    <button className="chat-launcher" onClick={onClick} aria-label="Open BondLens analyst">
      <Sparkles size={16} strokeWidth={2} />
      Ask BondLens
    </button>
  );
}
