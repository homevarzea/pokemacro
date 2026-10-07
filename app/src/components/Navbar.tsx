import { useContext } from "react";
import {
  FireIcon,
  Cog6ToothIcon,
  BellAlertIcon,
  BugAntIcon,
  HeartIcon,
  SparklesIcon,
  ClipboardDocumentListIcon,
} from "@heroicons/react/24/outline";

import * as RouterContext from "../contexts/RouterContext";
import * as GlobalContext from "../contexts/GlobalContext";
import * as AutoComboContext from "../contexts/AutoComboContext";
import {
  handleAutoCombo,
  handleAlert,
  handleHealing,
  handleAutoCatch,
  handleAutoRevive,
} from "../utils/actions";

const NavItem = ({
  active,
  icon: Icon,
  label,
  onClick,
  hasToggle = false,
  toggleActive = false,
  onToggle,
}: {
  active: boolean;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  hasToggle?: boolean;
  toggleActive?: boolean;
  onToggle?: () => void;
}) => {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onClick}
        className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 flex-1 text-left ${
          active
            ? "bg-blue-600 text-white"
            : "text-gray-300 hover:bg-gray-700 hover:text-white"
        }`}
      >
        <Icon className="w-4 h-4 flex-shrink-0" />
        <span>{label}</span>
      </button>

      {hasToggle && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          className={`
            relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 flex-shrink-0
            ${toggleActive ? "bg-blue-600" : "bg-gray-600"}
          `}
        >
          <span
            className={`
              inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200
              ${toggleActive ? "translate-x-5" : "translate-x-0.5"}
            `}
          />
          {toggleActive && (
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-400 rounded-full border border-gray-800"></div>
          )}
        </button>
      )}
    </div>
  );
};

const Navbar = () => {
  const router = useContext(RouterContext.Context);
  const {
    autoCombo,
    setAutoCombo,
    alertStatus,
    setAlertStatus,
    autoCatch,
    setAutoCatch,
    healing,
    setHealing,
    autoRevive,
    setAutoRevive,
  } = useContext(GlobalContext.Context);
  const { currentCombo } = useContext(AutoComboContext.Context);

  const toggleAlert = async () => {
    const result = await handleAlert();
    if (result.data) {
      setAlertStatus(result.data.alert_enabled);
    }
  };

  const toggleHealing = async () => {
    const result = await handleHealing();
    if (result.data) {
      setHealing(result.data.healing_enabled);
    }
  };

  const toggleAutoCombo = () => {
    setAutoCombo(!autoCombo);
    handleAutoCombo(currentCombo);
  };

  const toggleAutoCatch = async () => {
    const result = await handleAutoCatch();
    setAutoCatch(Boolean(result.auto_catch_enabled));
    if (result.error) window.alert(result.error);
  };

  const toggleAutoRevive = async () => {
    const result = await handleAutoRevive();
    if (result.data) {
      setAutoRevive(result.data.auto_revive_enabled);
    }
  };

  const navItems = [
    {
      route: RouterContext.Routes.AUTO_COMBO,
      icon: FireIcon,
      label: "Auto Combo",
      hasToggle: true,
      toggleActive: autoCombo,
      onToggle: toggleAutoCombo,
    },
    {
      route: RouterContext.Routes.ALERT,
      icon: BellAlertIcon,
      label: "Alert Settings",
      hasToggle: true,
      toggleActive: alertStatus,
      onToggle: toggleAlert,
    },
    {
      route: RouterContext.Routes.AUTO_CATCH,
      icon: BugAntIcon,
      label: "Auto Catch",
      hasToggle: true,
      toggleActive: autoCatch,
      onToggle: toggleAutoCatch,
    },
    {
      route: RouterContext.Routes.HEALING,
      icon: HeartIcon,
      label: "Healing",
      hasToggle: true,
      toggleActive: healing,
      onToggle: toggleHealing,
    },
    {
      route: RouterContext.Routes.AUTO_REVIVE,
      icon: SparklesIcon,
      label: "Auto Revive",
      hasToggle: true,
      toggleActive: autoRevive,
      onToggle: toggleAutoRevive,
    },
    {
      route: RouterContext.Routes.MOVE_BINDINGS,
      icon: Cog6ToothIcon,
      label: "Key Bindings",
      hasToggle: false,
    },
    {
      route: RouterContext.Routes.TODO,
      icon: ClipboardDocumentListIcon,
      label: "Todo List",
      hasToggle: false,
    },
  ];

  return (
    <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
      <div className="p-4 flex-1">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Tools & Modules
        </h2>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavItem
              key={item.route}
              active={router.currentRoute === item.route}
              icon={item.icon}
              label={item.label}
              onClick={() => router.setCurrentRoute(item.route)}
              hasToggle={item.hasToggle}
              toggleActive={item.toggleActive}
              onToggle={item.onToggle}
            />
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Navbar;
