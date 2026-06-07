import { TextInput, createTheme, ThemeProvider } from "flowbite-react";

const textInputTheme = createTheme({
    textInput: {
        field: {
            input: {
                base: "block w-full !bg-transparent border-[var(--dark-blue-300)] disabled:cursor-not-allowed disabled:opacity-50 transition-colors duration-150",
                colors: {
                    gray: "border-[var(--dark-blue-300)] !bg-transparent text-[var(--text)] placeholder-gray-400 focus:border-[var(--lighter-blue-600)] focus:ring-[var(--lighter-blue-600)]",
                    info: "border-[var(--dark-blue-300)] !bg-transparent text-[var(--text)] focus:border-[var(--lighter-blue-700)] focus:ring-[var(--lighter-blue-700)]",
                    failure: "border-red-500 bg-transparent text-red-900 placeholder-red-300 focus:border-red-600 focus:ring-red-600",
                    success: "border-emerald-500 bg-transparent text-emerald-900 placeholder-emerald-300 focus:border-emerald-600 focus:ring-emerald-600",
                },
                sizes: {
                    sm: "py-2.5 px-3 text-xs rounded-md",
                    md: "py-3.5 px-4 text-sm rounded-lg",
                    lg: "py-5 px-5 text-base rounded-xl",
                }
            }
        }
    }
});

export const CustomTextInput = ({
                                    color = "gray",
                                    sizes = "md",
                                    className = "",
                                    ...props
                                }) => {
    return (
        <ThemeProvider theme={textInputTheme}>
            <TextInput
                color={color}
                sizing={sizes}
                className={className}
                {...props}
            />
        </ThemeProvider>
    );
};