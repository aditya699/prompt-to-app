import { Header } from "@/components/Header";
import { ProjectGrid } from "@/features/home/ProjectGrid";
import { PromptBox } from "@/features/home/PromptBox";
import { ProjectPage } from "@/features/project/ProjectPage";
import { useRoute } from "@/lib/router";

export default function App() {
  const route = useRoute();
  return (
    <div className="min-h-screen">
      <Header />
      <main className="px-4 py-8 sm:py-12">
        {route.page === "project" ? (
          <ProjectPage key={route.id} id={route.id} />
        ) : (
          <>
            <PromptBox />
            <ProjectGrid />
          </>
        )}
      </main>
    </div>
  );
}
