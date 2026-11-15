// A tiny hash router: two pages don't need a routing library.
//   #/            -> home
//   #/p/12        -> project 12
import { useEffect, useState } from "react";

export type Route = { page: "home" } | { page: "project"; id: number };

function parse(hash: string): Route {
  const match = /^#\/p\/(\d+)/.exec(hash);
  return match ? { page: "project", id: Number(match[1]) } : { page: "home" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function navigate(route: Route) {
  window.location.hash = route.page === "project" ? `/p/${route.id}` : "/";
  window.scrollTo({ top: 0 });
}
