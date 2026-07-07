import {Button, createTheme, ThemeProvider} from "flowbite-react"


const buttonTheme = createTheme({
    button: {
        // base: "ring-2",
        color: {
            primary: "bg-[var(--lighter-blue-600)] text-white hover:bg-[var(--lighter-blue-700)] focus:ring-[var(--accent-border)] focus:ring-3",
            },
        outline: {
            base: "ring-2"
        }
    },
});

export const CustomButton = ({
                                 children,
                                 color = "primary",
                                 className = "",
                                 ...props
                             }) => {
    return (
        <ThemeProvider theme={buttonTheme}>
            <Button
                color={color}
                className={className}
                {...props}
            >
                {children}
            </Button>
        </ThemeProvider>
    );
};