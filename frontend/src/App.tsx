// The app: the room, the language and the toast region around the current place. The places (realm, cabinet,
// drawer, slide, stage, contribute, identify, profile, about) arrive with U10 to U15; until then every path shows the
// specimen place of the visual system (U9).
import { RoomProvider } from "./design/theme";
import { LanguageProvider } from "./i18n";
import { DesignPlace } from "./places/design/DesignPlace";
import { ToastRegion } from "./ui/Overlay";

export function App() {
  return (
    <RoomProvider>
      <LanguageProvider>
        <ToastRegion>
          <DesignPlace />
        </ToastRegion>
      </LanguageProvider>
    </RoomProvider>
  );
}
