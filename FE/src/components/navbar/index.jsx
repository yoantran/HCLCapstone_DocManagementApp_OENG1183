// export const customNavbarTheme = {
//     root: {
//         base: "min-h-12 h-auto md:h-12 w-full flex items-center px-4 md:px-6 !bg-(--dark-blue-700) border-b !border-(--cool-gray-200) py-2 md:py-0 relative z-50",
//         inner: {
//             base: "mx-auto flex-wrap md:flex-nowrap flex w-full h-full items-center justify-between p-0 bg-transparent"
//         }
//     },
//     toggle: {
//         base: "inline-flex items-center rounded-lg p-1.5 text-sm text-(--cool-gray-500) hover:bg-(--dark-blue-800) hover:text-white focus:outline-none focus:ring-2 focus:ring-(--cool-gray-500) md:hidden",
//         icon: "h-6 w-6 shrink-0"
//     },
//     collapse: {
//         base: "absolute right-4 top-14 z-50 w-56 md:static md:w-auto md:top-auto md:right-auto md:block shadow-2xl rounded-lg border border-slate-800 bg-(--dark-blue-700) md:bg-transparent md:border-none md:shadow-none focus:outline-none py-0",
//         list: "m-0 p-1 md:p-0 flex flex-col md:flex-row md:space-x-6 text-sm font-medium tracking-wide items-stretch md:items-center bg-transparent gap-0.5 md:gap-0"
//     },
//     link: {
//         base: "block w-full md:w-auto no-underline text-(--ch-light-canvas) border-b border-(--cool-gray-200) transition-colors duration-200 py-2 px-3 md:py-1 md:px-2 rounded-md md:rounded-none",
//         active: {
//             on: "text-(--lighter-blue-600) dark:text-[#2e74ff] font-semibold bg-(--dark-blue-700) md:bg-transparent",
//             off: "text-(--cool-gray-500) hover:text-white hover:bg-(--dark-blue-700) md:hover:bg-transparent"
//         }
//     },
// };


export const customNavbarTheme = {
    root: {
        base: "min-h-12 h-auto md:h-12 w-full flex items-center px-4 md:px-6 !bg-(--dark-blue-700) border-b !border-(--cool-gray-200) py-2 md:py-0 relative z-50",
        inner: {
            base: "mx-auto flex-wrap md:flex-nowrap flex w-full h-full items-center justify-between p-0 bg-transparent"
        }
    },
    toggle: {
        base: "inline-flex items-center justify-center rounded-lg p-1.5 text-sm text-(--cool-gray-500) hover:bg-slate-700/30 hover:text-white focus:outline-none focus:ring-2 focus:ring-(--cool-gray-500) md:hidden transition-opacity duration-[160ms] ease-out",
        icon: "h-6 w-6 shrink-0"
    },
    collapse: {
        // Floating dropdown card on mobile matching the user menu's exact background, border, and shadow
        base: "absolute right-4 top-14 z-50 w-64 md:static md:w-auto md:top-auto md:right-auto md:block shadow-2xl rounded-lg border border-slate-800 bg-(--dark-blue-700) md:bg-transparent md:border-none md:shadow-none focus:outline-none overflow-hidden",
        list: "m-0 p-0 flex flex-col md:flex-row md:space-x-6 text-sm font-medium tracking-wide items-stretch md:items-center bg-transparent"
    },
    link: {
        // Clean item styling without individual bottom borders, matching the View My Profile menu item
        base: "flex w-full md:w-auto cursor-pointer items-center justify-start px-4 py-3 md:py-1 md:px-2 text-left text-sm font-normal text-(--ch-cool-gray) hover:text-white hover:bg-slate-700/30 md:hover:bg-transparent focus:bg-slate-700/30 transition-colors duration-[160ms] ease-out no-underline border-none",
        active: {
            on: "text-white font-semibold bg-slate-700/30 md:bg-transparent md:text-(--lighter-blue-300)",
            off: "text-(--ch-cool-gray) hover:text-white hover:bg-slate-700/30 md:hover:bg-transparent"
        }
    }
};