import { Layout } from "@/components/layout";
import { DirectGPT4OChat } from "@/components/direct-gpt4o-chat";

export default function GPT4OChatPage() {
  return (
    <Layout title="GPT-4o Chat">
      <div className="container mx-auto h-[calc(100vh-12rem)]">
        <DirectGPT4OChat />
      </div>
    </Layout>
  );
}