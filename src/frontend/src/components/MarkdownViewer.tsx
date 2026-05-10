import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
  onLinkClick?: (target: string) => void;
};

export function MarkdownViewer({ content, onLinkClick }: Props) {
  const processedContent = content.replace(
    /\[\[([^\]]+)\]\]/g,
    (_, rawTarget) => {
      const [target, label = target] = String(rawTarget).split("|");
      return `[${label.trim()}](wiki:${encodeURIComponent(target.trim())})`;
    }
  );

  return (
    <div className="markdown-viewer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => {
          if (url.startsWith("wiki:")) return url;
          return defaultUrlTransform(url);
        }}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("wiki:")) {
              const target = decodeURIComponent(href.replace("wiki:", ""));
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
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
