import { Hourglass } from 'flowbite-react-icons/outline';
// Define the central dictionary map
const iconMap = {
    'hour-glass': Hourglass,
};

// Unified Icon Wrapper Component
export const Icon = ({ name, size = '24', className = '', ...props }) => {
    const IconComponent = iconMap[name];

    if (!IconComponent) {
        console.warn(`Icon "${name}" does not exist in the flowbite iconMap.`);
        return null;
    }

    return (
        <IconComponent
            size={size}
            className={`${className}`}
            {...props}
        />
    );
};
