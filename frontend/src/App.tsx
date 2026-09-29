// The app: the room, the language, the session, the tree and the toast region around the place the address names.
// The identify, profile and about places arrive with U13 to U15. The contribute places load as their own chunk.
import { lazy, Suspense } from "react";
import { Route, Switch } from "wouter";
import { SessionProvider } from "./account/session";
import { RoomProvider } from "./design/theme";
import { LanguageProvider } from "./i18n";
import { ForgotPlace, JoinPlace, ResetPlace, SignInPlace } from "./places/account/AccountPlaces";
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
import { Skeleton } from "./ui/Feedback";

const ContributeList = lazy(() => import("./places/contribute/ContributeList").then((m) => ({ default: m.ContributeList })));
const CaseEditor = lazy(() => import("./places/contribute/CaseEditor").then((m) => ({ default: m.CaseEditor })));
const waiting = <Skeleton lines={6} />;

export function App() {
  return (
    <RoomProvider>
      <LanguageProvider>
        <SessionProvider>
        <TreeProvider>
          <ToastRegion>
            <Switch>
              <Route path="/" component={RealmsPlace} />
              <Route path="/c/*" component={CollectionPlace} />
              <Route path="/search" component={SearchPlace} />
              <Route path="/map" component={MapPlace} />
              <Route path="/s/:id" component={SlidePlace} />
              <Route path="/s/:id/stage/:asset" component={StagePlace} />
              <Route path="/signin" component={SignInPlace} />
              <Route path="/join" component={JoinPlace} />
              <Route path="/forgot-password" component={ForgotPlace} />
              <Route path="/reset-password" component={ResetPlace} />
              <Route path="/contribute"><Suspense fallback={waiting}><ContributeList /></Suspense></Route>
              <Route path="/contribute/new"><Suspense fallback={waiting}><CaseEditor /></Suspense></Route>
              <Route path="/contribute/:id"><Suspense fallback={waiting}><CaseEditor /></Suspense></Route>
              <Route path="/design" component={DesignPlace} />
              <Route component={NotFoundPlace} />
            </Switch>
          </ToastRegion>
        </TreeProvider>
        </SessionProvider>
      </LanguageProvider>
    </RoomProvider>
  );
}
