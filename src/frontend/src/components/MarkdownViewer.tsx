import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
  onLinkClick?: (target: string) => void;
};

export function MarkdownViewer({ content, onLinkClick }: Props) {
  const processedContent = content.replace(
    /\[\[([^\]]+)\]\]/g,
    (_, target) => `[${target}](wiki://${encodeURIComponent(target)})`
  );

  return (
    <div className="markdown-viewer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("wiki://")) {
              const target = decodeURIComponent(href.replace("wiki://", ""));
              return (
                <a
                  href="#"
                  className="wikilink"
                  onClick={(e) => {
                    e.preventDefault();
                    onLinkClick?.(target);
                  }}
                >
                  {children}
                </a>
              );
            }
            return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
          },
        }}
      />
    </div>
  );
}
