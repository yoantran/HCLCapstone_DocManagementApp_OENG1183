export const customNavbarTheme = {
    root: {
        base: "h-[65px] w-full flex items-center px-6 !bg-(--dark-blue-700) border-b !border-(--cool-gray-200) py-0",
        inner: {
            base: "mx-auto flex w-full h-full items-center justify-between p-0 bg-transparent"
        }
    },
    collapse: {
        base: "w-full md:block md:w-auto",
        list: "m-0 p-0 flex flex-col md:flex-row md:space-x-8 text-sm font-medium tracking-wide items-center bg-transparent"
    },
    link: {
        base: "block no-underline text-(--cool-gray-500) hover:text-white transition-colors duration-200 py-1 px-2 bg-transparent md:bg-transparent",
        active: {
            on: "text-(--lighter-blue-600) dark:text-[#2e74ff] font-semibold bg-transparent md:bg-transparent",
            off: "text-(--cool-gray-500) hover:text-white bg-transparent md:bg-transparent"
        }
    }
};