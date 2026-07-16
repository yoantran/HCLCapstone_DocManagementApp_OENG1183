export const LeftArrowIcon = ({ currPage }) => (
    <svg disabled={currPage <= 1} className="w-6 h-6 dark:text-white disabled:cursor-default hover:cursor-pointer text-white" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"
        width="24" height="24" fill="none" viewBox="0 0 24 24">
        <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
            d="m15 19-7-7 7-7" />
    </svg>
)