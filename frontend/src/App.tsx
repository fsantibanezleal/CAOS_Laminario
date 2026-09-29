// The app: the room, the language, the tree and the toast region around the place the address names. The contribute,
// identify, profile and about places arrive with U12 to U15.
import { Route, Switch } from "wouter";
import { RoomProvider } from "./design/theme";
import { LanguageProvider } from "./i18n";
import { CollectionPlace } from "./places/cabinet/CollectionPlace";
import { DesignPlace } from "./places/design/DesignPlace";
import { MapPlace } from "./places/map/MapPlace";
import { NotFoundPlace } from "./places/NotFoundPlace";
import { RealmsPlace } from "./places/realms/RealmsPlace";
import { SearchPlace } from "./places/search/SearchPlace";
import { SlidePlace } from "./places/slide/SlidePlace";
import { StagePlace } from "./places/stage/StagePlace";
import "./router/navigation";
import { TreeProvider } from "./tree/TreeProvider";
import { ToastRegion } from "./ui/Overlay";

export function App() {
  return (
    <RoomProvider>
      <LanguageProvider>
        <TreeProvider>
          <ToastRegion>
            <Switch>
              <Route path="/" component={RealmsPlace} />
              <Route path="/c/*" component={CollectionPlace} />
              <Route path="/search" component={SearchPlace} />
              <Route path="/map" component={MapPlace} />
              <Route path="/s/:id" component={SlidePlace} />
              <Route path="/s/:id/stage/:asset" component={StagePlace} />
              <Route path="/design" component={DesignPlace} />
              <Route component={NotFoundPlace} />
            </Switch>
          </ToastRegion>
        </TreeProvider>
      </LanguageProvider>
    </RoomProvider>
  );
}
