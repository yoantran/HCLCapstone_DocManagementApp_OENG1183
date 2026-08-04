import { BsGithub, BsGlobe } from 'react-icons/bs';

export default function Footer({ className = "" }) {
    return (
        <footer
            className={`w-full text-(--lighter-blue-300) text-sm rounded-2xl px-8 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${className}`}
        >
            <div>
                © {new Date().getFullYear()} The Chosen One. All rights reserved.
            </div>

            <div className="flex items-center gap-4">
                <a
                    href="https://github.com/yoantran/HCLCapstone_DocManagementApp_OENG1183"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-(--ch-cool-gray) transition-colors"
                    aria-label="GitHub"
                >
                    <BsGithub className="w-4 h-4" />
                </a>
                <a
                    href="https://example.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-(--ch-cool-gray) transition-colors"
                    aria-label="Website"
                >
                    <BsGlobe className="w-4 h-4" />
                </a>
            </div>
        </footer>
    );
}