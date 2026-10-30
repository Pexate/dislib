import { mount } from "svelte";
import "./lib/styles/app.css";
import App from "./App.svelte";

mount(App, {
  target: document.getElementById("root")!,
});
